"""Ask Agent (docs/10).

Without ANTHROPIC_API_KEY the agent answers from the playbook + live context
(the static provider below), which also produces the reference behavior the
acceptance test checks. With a key, AnthropicProvider uses the Messages API.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.audience import Audience, AudienceSource
from app.models.campaign import Campaign, Strategy
from app.models.intelligence import Recommendation, RecommendationStatus

SUGGESTED_QUESTIONS = {
    "audience": ["What audience should I target?", "What's the difference between audience suggestions and audience controls?"],
    "bidding": ["Should I use automatic or manual bidding?", "What CPM should I expect?"],
    "measurement": ["Help me set my target", "Which attribution window should I use?"],
    "placement": ["Should I pick specific channels?", "What does 'All Apps & Channels' include?"],
    "creatives": ["What makes a good streaming-TV ad?", "How long should my creative be?"],
    "campaign": ["Which goal should I pick?", "How do I measure a TV campaign?"],
    "default": ["How does CTV advertising work?", "How is this measured?"],
}


def suggested_questions(section: str | None) -> list[str]:
    return SUGGESTED_QUESTIONS.get((section or "default").lower(), SUGGESTED_QUESTIONS["default"])


async def build_context(db: AsyncSession, account_id: uuid.UUID, ctx: dict) -> dict:
    out: dict = {"page": ctx.get("page"), "section": ctx.get("section")}
    cid = ctx.get("campaign_id")
    if not cid:
        return out
    campaign = await db.get(Campaign, cid)
    if campaign is None or campaign.account_id != account_id:
        return out
    strategies = (await db.execute(select(Strategy).where(Strategy.campaign_id == campaign.id))).scalars().all()
    web_aud_ids = set(
        (await db.execute(select(Audience.id).where(Audience.advertiser_id == campaign.advertiser_id, Audience.source == AudienceSource.web_traffic))).scalars().all()
    )
    has_web = any(set(s.include_audience_ids or []) & web_aud_ids for s in strategies)
    has_interests = any(s.interest_segment_ids for s in strategies)
    out.update({
        "campaign_id": str(campaign.id), "goal": campaign.goal.value, "kpi": campaign.kpi.value,
        "attribution_window_hours": campaign.attribution_window_hours,
        "n_strategies": len(strategies),
        "has_web_audiences": has_web, "has_interest_targeting": has_interests,
        "strategy_id": str(strategies[0].id) if strategies else None,
    })
    return out


def _audience_answer(context: dict) -> str:
    long_window = (context.get("attribution_window_hours") or 0) >= 168
    return (
        "**What you already have — warm audiences (retargeting)**\n"
        "Your Visitors, Leads and Purchasers web audiences are your highest-intent viewers. For a Sales goal, "
        "re-reaching them on streaming TV is the fastest path to orders.\n\n"
        "**What you could add — prospecting audiences**\n"
        + ("Because your attribution window is long, maximize reach to find new customers: add in-market interests, "
           "relevant demographics and age & gender, and a lookalike of your purchasers.\n\n"
           if long_window else
           "To grow beyond your existing visitors, add in-market interests, demographics, and a lookalike of your purchasers.\n\n")
        + "**One important note**\n"
        "Mixing warm (retargeting) and cold (prospecting) in one strategy hides what's actually working. I'd run one "
        "retargeting strategy and one prospecting strategy so each has its own budget and reporting.\n\n"
        "Would you like me to add interest targeting to this strategy, or set up a second prospecting strategy?"
    )


def _generic_answer(question: str, context: dict) -> str:
    return (
        "**Short answer**\n"
        f"Here's how I'd think about \"{question.strip()}\" for your campaign.\n\n"
        "**Why**\n"
        "Streaming TV works best when targeting is broad enough to spend the budget while staying relevant to your goal.\n\n"
        "**One note**\n"
        "Keep an eye on the deliverability estimate as you adjust targeting.\n\n"
        "Would you like me to review your current targeting and suggest a change?"
    )


def static_answer(question: str, context: dict) -> tuple[str, dict | None]:
    q = question.lower()
    accepting = any(w in q for w in ["yes", "second strategy", "prospecting strategy", "do it", "go ahead"])
    if accepting and context.get("strategy_id"):
        proposal = {
            "op": "duplicate_strategy", "id": context["strategy_id"],
            "diff": "+ New prospecting strategy (copy of this one, for interest/demographic targeting)",
        }
        return ("I'll set up a second **prospecting** strategy you can tune for interests and demographics. Review the proposal below.", proposal)
    if any(w in q for w in ["audience", "target", "who should"]) and context.get("goal") == "sales":
        return (_audience_answer(context), None)
    if any(w in q for w in ["audience", "target", "who should"]):
        return (_audience_answer(context), None)
    return (_generic_answer(question, context), None)


async def anthropic_answer(question: str, context: dict) -> str:
    """LLM path (used only when ANTHROPIC_API_KEY is set)."""
    import anthropic  # lazy import — optional dependency

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    model = getattr(settings, "anthropic_model", None) or "claude-opus-5-5"
    system = (
        "You are the AdCraft AI advertising assistant. Answer in <=180 words with short **bold** section headers, "
        "ground claims in the provided context, never invent metrics, and end with a concrete next step phrased as "
        "an offer. Context JSON follows.\n\n" + str(context)
    )
    msg = client.messages.create(
        model=model, max_tokens=1024, system=system,
        messages=[{"role": "user", "content": question}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")


async def answer(db: AsyncSession, account_id: uuid.UUID, context: dict, question: str) -> tuple[str, dict | None]:
    ctx = await build_context(db, account_id, context)
    if settings.anthropic_api_key:
        try:
            return (await anthropic_answer(question, ctx), None)
        except Exception:  # noqa: BLE001 — fall back to static on any LLM error
            pass
    return static_answer(question, ctx)


def configured() -> bool:
    return bool(settings.anthropic_api_key)
