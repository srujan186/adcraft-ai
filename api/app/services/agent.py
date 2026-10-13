"""Ask Agent (docs/10).

The agent answers through Claude, grounded in a context built from live account data: the
campaign, its tracking, audiences and their sizes, every strategy's targeting, bidding,
creatives and delivery estimate, publish validation issues, open recommendations and the last
14 days of results.

Without ANTHROPIC_API_KEY, or when the call fails, the agent says it is unavailable and offers
help articles. It never falls back to canned advice: canned text cannot see the account, and
the old fallback told every user their web audiences were their "highest-intent viewers" even
when they had no pixel and no audiences.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import statistics
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.advertiser import Advertiser
from app.models.audience import Audience
from app.models.campaign import BiddingMode, Campaign, CampaignGoal, Strategy, StrategyCreative
from app.models.creative import Creative
from app.models.intelligence import Recommendation, RecommendationStatus
from app.models.inventory import Channel, InterestSegment
from app.models.measurement import StatsDaily
from app.models.tracking import App, Pixel, PixelEventType
from app.services.estimator import estimate
from app.services.validation import MIN_DAILY_MICROS, _strategy_to_dict, validate_campaign

log = logging.getLogger(__name__)

# An audience smaller than this can't carry a strategy; the agent must not present it as usable.
MIN_AUDIENCE_HOUSEHOLDS = 1_000
METRICS_DAYS = 14
FALLBACK_BETA = "server-side-fallback-2026-07-01"

SUGGESTED_QUESTIONS = {
    "audience": ["What audience should I target?", "What's the difference between audience suggestions and audience controls?"],
    "bidding": ["Should I use automatic or manual bidding?", "What CPM should I expect?"],
    "measurement": ["Help me set my target", "Which attribution window should I use?"],
    "placement": ["Should I pick specific channels?", "What does 'All Apps & Channels' include?"],
    "creatives": ["What makes a good streaming-TV ad?", "How long should my creative be?"],
    "campaign": ["Which goal should I pick?", "How do I measure a TV campaign?"],
    "default": ["How does CTV advertising work?", "How is this measured?"],
}

# Mirrors web/src/content/help.ts (tests/test_agent.py keeps the two in step).
HELP_ARTICLES = {
    "how-ctv-advertising-works": "How streaming-TV advertising works",
    "how-billing-works": "How billing works",
    "measurement-and-attribution": "Measurement & attribution",
    "set-up-your-pixel": "Set up your pixel",
    "audiences-explained": "Audiences: warm vs. cold",
    "setting-your-budget": "Setting your budget",
}
_HELP_KEYWORDS = [
    (("audience", "target", "retarget", "prospect", "who should"), ["audiences-explained", "set-up-your-pixel"]),
    (("pixel", "track", "event", "tag"), ["set-up-your-pixel", "measurement-and-attribution"]),
    (("measure", "attribution", "roas", "kpi", "conversion", "result"), ["measurement-and-attribution"]),
    (("budget", "spend", "cpm", "bid", "cost"), ["setting-your-budget", "how-billing-works"]),
    (("bill", "invoice", "payment", "charge", "fund"), ["how-billing-works"]),
]
_HELP_BY_SECTION = {
    "audience": "audiences-explained", "measurement": "measurement-and-attribution",
    "bidding": "setting-your-budget", "campaign": "how-ctv-advertising-works",
}

UNAVAILABLE = (
    "The assistant isn't available right now, so it can't review your account or give advice on it. "
    "These help articles may answer your question:"
)
REFUSED = (
    "I can't help with that one. I can answer questions about your campaigns: targeting, budget, "
    "bidding, creatives, tracking and results."
)

SYSTEM_PROMPT = """\
You are the assistant inside AdCraft, a self-serve platform for buying streaming-TV (CTV) ads. \
The person you're talking to is an advertiser managing their own campaigns.

Each user turn begins with a <context> block: a JSON snapshot of their account, read from the \
database a moment ago. It is the only source of facts about their account.

How to use the context:
- Every statement about their account (what is set up, what is missing, sizes, prices, \
results) must come from <context>. If something isn't there, say you can't see it; never guess.
- "tracking.pixel" is "none" when no pixel is installed. Web audiences (visitors, leads, \
purchasers) only fill from a pixel, so without one there is nothing to retarget: say so and \
point them to prospecting (interests, demographics, location) instead.
- "audiences.usable" lists audiences with at least 1,000 households. Never describe an audience \
as available, worth targeting or high intent unless it is in that list. Audiences in \
"audiences.too_small" exist but are too small to target yet; say that plainly if they come up.
- Money values are already formatted in US dollars. For manual bidding, compare the strategy's \
max CPM with "inventory.median_cpm_floor" and "inventory.cheapest_cpm_floor": below the \
cheapest floor it can win almost nothing; below the median it will under-deliver.
- "validation_issues" are what currently blocks or weakens publishing; mention the ones \
relevant to the question.
- "metrics_last_14_days" are real delivered results; zeros mean nothing has delivered yet. \
Don't invent benchmarks or results. General advice about how CTV works is fine when it is \
clearly general, not a claim about their account.

How to answer:
- At most about 180 words. Use 2-3 short sections, each starting with a **bold** header on its \
own line. Plain lines and "- " bullets only: no tables, no # headings.
- Be direct. Lead with the answer to the question that was asked.
- End with one concrete next step, phrased as an offer.
- If they ask for, or agree to, a change you can express with the propose_change tool, call it. \
The change is shown to them as a proposal they apply themselves; say that it's ready to review. \
When you use a tool, you may say a brief sentence first. If no tool can express what they \
asked for, tell them where in the product to make the change instead.
- Do not include internal or system XML tags in your response.
"""

PROPOSE_CHANGE_TOOL = {
    "name": "propose_change",
    "description": (
        "Propose a change to one of the user's strategies. Nothing changes until the user clicks "
        "Apply on the proposal. Use 'update_strategy' with one or more of budget_usd, max_cpm_usd, "
        "bidding_mode; use 'duplicate_strategy' to copy a strategy so it can be tuned separately "
        "(for example to split retargeting from prospecting). strategy_id must be an id from "
        "context.strategies."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": ["update_strategy", "duplicate_strategy"]},
            "strategy_id": {"type": "string"},
            "budget_usd": {"type": "number", "description": "New daily (or lifetime) budget in US dollars, at least 50/day."},
            "max_cpm_usd": {"type": "number", "description": "New manual max CPM in US dollars. Implies manual bidding."},
            "bidding_mode": {"type": "string", "enum": ["automatic", "manual"]},
            "summary": {"type": "string", "description": "One line describing the change for the user."},
        },
        "required": ["op", "strategy_id"],
    },
}


def suggested_questions(section: str | None) -> list[str]:
    return SUGGESTED_QUESTIONS.get((section or "default").lower(), SUGGESTED_QUESTIONS["default"])


def help_for(question: str, section: str | None) -> list[dict]:
    q = question.lower()
    slugs: list[str] = []
    for words, picks in _HELP_KEYWORDS:
        if any(w in q for w in words):
            slugs += picks
    if section and section.lower() in _HELP_BY_SECTION:
        slugs.append(_HELP_BY_SECTION[section.lower()])
    slugs.append("how-ctv-advertising-works")
    seen = list(dict.fromkeys(slugs))[:3]
    return [{"title": HELP_ARTICLES[s], "href": f"/help/{s}"} for s in seen]


# ── live context ───────────────────────────────────────────────────────────────
def _usd(micros: int | float | None) -> str | None:
    return None if micros is None else f"${micros / 1_000_000:,.2f}"


def _uuid(v) -> uuid.UUID | None:
    try:
        return v if isinstance(v, uuid.UUID) else uuid.UUID(str(v))
    except (TypeError, ValueError):
        return None


def _audience_entry(a: Audience) -> dict:
    return {"id": str(a.id), "name": a.name, "source": a.source.value, "status": a.status.value,
            "households": int(a.matched_households or 0)}


async def _tracking(db: AsyncSession, campaign: Campaign) -> dict:
    if campaign.goal == CampaignGoal.app_promotion:
        app = (await db.execute(select(App).where(App.advertiser_id == campaign.advertiser_id))).scalars().first()
        return {"app": app.status.value if app else "none",
                "last_postback_at": app.last_postback_at.isoformat() if app and app.last_postback_at else None}
    pixel = (await db.execute(select(Pixel).where(Pixel.advertiser_id == campaign.advertiser_id))).scalars().first()
    if pixel is None:
        return {"pixel": "none", "events_seen_last_7_days": []}
    week_ago = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)
    types = (await db.execute(select(PixelEventType).where(PixelEventType.pixel_id == pixel.id))).scalars().all()
    return {
        "pixel": pixel.status.value,
        "events_seen_last_7_days": sorted(
            t.custom_name or t.event.value for t in types if t.last_seen_at and t.last_seen_at >= week_ago),
        "last_event_at": pixel.last_event_at.isoformat() if pixel.last_event_at else None,
    }


async def _strategy(db: AsyncSession, s: Strategy, goal: CampaignGoal, audiences: dict[uuid.UUID, dict]) -> dict:
    creatives = (await db.execute(
        select(Creative).join(StrategyCreative, StrategyCreative.creative_id == Creative.id)
        .where(StrategyCreative.strategy_id == s.id))).scalars().all()
    interests = []
    if s.interest_segment_ids:
        interests = (await db.execute(
            select(InterestSegment.name).where(InterestSegment.id.in_(s.interest_segment_ids)))).scalars().all()
    channels = []
    if s.placement_mode.value == "selected" and s.channel_ids:
        channels = (await db.execute(select(Channel.name).where(Channel.id.in_(s.channel_ids)))).scalars().all()

    def auds(ids):
        out = []
        for i in ids or []:
            a = audiences.get(i)
            out.append({"name": a["name"], "households": a["households"],
                        "usable": a["households"] >= MIN_AUDIENCE_HOUSEHOLDS} if a else {"name": "(deleted audience)"})
        return out

    est = await estimate(db, goal, _strategy_to_dict(s))
    bidding = {"mode": s.bidding_mode.value}
    if s.bidding_mode == BiddingMode.manual:
        bidding["max_cpm"] = _usd(s.max_cpm_micros)
    return {
        "id": str(s.id), "name": s.name, "status": s.status.value,
        "budget": {"type": s.budget_type.value, "amount": _usd(s.budget_micros),
                   "minimum_per_day": _usd(MIN_DAILY_MICROS)},
        "dates": {"start": s.start_date.isoformat() if s.start_date else None,
                  "end": s.end_date.isoformat() if s.end_date else None},
        "bidding": bidding,
        "placement": {"mode": s.placement_mode.value, "channels": list(channels),
                      "devices": list(s.device_types or []), "live_sports_only": s.live_sports_only},
        "locations": s.locations or {},
        "dayparting": (s.dayparting or {}).get("preset", "any"),
        "interests": list(interests),
        "demographics": s.demographics or {},
        "audiences": {"include": auds(s.include_audience_ids), "exclude": auds(s.exclude_audience_ids)},
        "creatives": [{"name": c.name, "review_status": c.review_status.value,
                       "duration_seconds": round(c.duration_ms / 1000) if c.duration_ms else None}
                      for c in creatives],
        "estimate": {
            "audience_households": est["audience_households"],
            "weekly_impressions": est["weekly"]["impressions"],
            "deliverability": est["deliverability"],
            "expected_cpm": _usd(est["expected_cpm_micros"]),
            "messages": est["messages"],
        },
    }


async def _metrics(db: AsyncSession, campaign_id: uuid.UUID) -> dict:
    since = dt.date.today() - dt.timedelta(days=METRICS_DAYS - 1)
    cols = (StatsDaily.impressions, StatsDaily.spend_micros, StatsDaily.sessions, StatsDaily.leads,
            StatsDaily.purchases, StatsDaily.installs, StatsDaily.revenue_micros)
    rows = (await db.execute(
        select(StatsDaily.date, *[func.coalesce(func.sum(c), 0) for c in cols])
        .where(StatsDaily.campaign_id == campaign_id, StatsDaily.date >= since)
        .group_by(StatsDaily.date).order_by(StatsDaily.date))).all()
    tot = [sum(int(r[i + 1]) for r in rows) for i in range(len(cols))]
    imps, spend, sessions, leads, purchases, installs, revenue = tot
    return {
        "from": since.isoformat(), "to": dt.date.today().isoformat(),
        "impressions": imps, "spend": _usd(spend), "sessions": sessions, "leads": leads,
        "purchases": purchases, "installs": installs, "revenue": _usd(revenue),
        "cpm": _usd(spend * 1000 / imps) if imps else None,
        "roas": round(revenue / spend, 2) if spend else None,
        "by_day": [{"date": r[0].isoformat(), "impressions": int(r[1]), "spend": _usd(int(r[2]))} for r in rows],
    }


async def build_context(db: AsyncSession, account_id: uuid.UUID, ctx: dict) -> dict:
    out: dict = {"page": ctx.get("page"), "section": ctx.get("section"), "today": dt.date.today().isoformat()}
    cid = _uuid(ctx.get("campaign_id"))
    campaign = await db.get(Campaign, cid) if cid else None
    if campaign is None or str(campaign.account_id) != str(account_id):
        camps = (await db.execute(
            select(Campaign).where(Campaign.account_id == _uuid(account_id))
            .order_by(Campaign.created_at.desc()).limit(20))).scalars().all()
        out["campaigns"] = [{"name": c.name, "status": c.status.value, "goal": c.goal.value} for c in camps]
        return out

    advertiser = await db.get(Advertiser, campaign.advertiser_id)
    aud_rows = (await db.execute(
        select(Audience).where(Audience.advertiser_id == campaign.advertiser_id, Audience.archived_at.is_(None))
    )).scalars().all()
    audiences = {a.id: _audience_entry(a) for a in aud_rows}
    strategies = (await db.execute(
        select(Strategy).where(Strategy.campaign_id == campaign.id).order_by(Strategy.position))).scalars().all()
    floors = sorted((await db.execute(select(Channel.base_cpm_micros))).scalars().all())
    recs = (await db.execute(
        select(Recommendation).where(Recommendation.campaign_id == campaign.id,
                                     Recommendation.status == RecommendationStatus.open))).scalars().all()

    target = None
    if campaign.kpi_target_micros is not None:
        target = _usd(campaign.kpi_target_micros)
    elif campaign.kpi_target_ratio is not None:
        target = f"{float(campaign.kpi_target_ratio):g}x"

    out.update({
        "advertiser": {"name": advertiser.name, "website": advertiser.website_url} if advertiser else None,
        "campaign": {
            "id": str(campaign.id), "name": campaign.name, "status": campaign.status.value,
            "goal": campaign.goal.value, "kpi": campaign.kpi.value, "kpi_target": target,
            "attribution_window_hours": campaign.attribution_window_hours,
            "blocked_reason": campaign.blocked_reason,
        },
        "tracking": await _tracking(db, campaign),
        "audiences": {
            "minimum_households": MIN_AUDIENCE_HOUSEHOLDS,
            "usable": [a for a in audiences.values() if a["households"] >= MIN_AUDIENCE_HOUSEHOLDS],
            "too_small": [a for a in audiences.values() if a["households"] < MIN_AUDIENCE_HOUSEHOLDS],
        },
        "strategies": [await _strategy(db, s, campaign.goal, audiences) for s in strategies],
        "inventory": {
            "channels": len(floors),
            "median_cpm_floor": _usd(statistics.median(floors)) if floors else None,
            "cheapest_cpm_floor": _usd(floors[0]) if floors else None,
        },
        "validation_issues": [
            {k: i[k] for k in ("level", "code", "message", "field")} for i in await validate_campaign(db, campaign)],
        "open_recommendations": [{"title": r.title, "detail": r.body} for r in recs],
        "metrics_last_14_days": await _metrics(db, campaign.id),
    })
    return out


# ── Claude ─────────────────────────────────────────────────────────────────────
_anthropic_client = None


def _client():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic

        _anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=90.0, max_retries=2)
    return _anthropic_client


def _messages(history: list[dict], context: dict, question: str) -> list[dict]:
    msgs = [{"role": m["role"], "content": m["text"]} for m in history if m.get("text")]
    msgs.append({"role": "user", "content": [
        {"type": "text", "text": f"<context>\n{json.dumps(context, default=str)}\n</context>"},
        {"type": "text", "text": question},
    ]})
    return msgs


def _proposal(args: dict, context: dict) -> dict | None:
    """Turn a propose_change call into a stored action, or None if it doesn't check out."""
    strategy = next((s for s in context.get("strategies", []) if s["id"] == str(args.get("strategy_id"))), None)
    if strategy is None:
        return None
    if args.get("op") == "duplicate_strategy":
        return {"op": "duplicate_strategy", "id": strategy["id"],
                "diff": args.get("summary") or f"+ New strategy: a copy of “{strategy['name']}” to tune separately"}
    if args.get("op") != "update_strategy":
        return None

    patch: dict = {}
    lines: list[str] = []
    if isinstance(args.get("budget_usd"), (int, float)) and args["budget_usd"] > 0:
        patch["budget_micros"] = round(args["budget_usd"] * 1_000_000)
        lines.append(f"Budget: {strategy['budget']['amount']} → {_usd(patch['budget_micros'])}")
    if isinstance(args.get("max_cpm_usd"), (int, float)) and args["max_cpm_usd"] > 0:
        patch["max_cpm_micros"] = round(args["max_cpm_usd"] * 1_000_000)
        patch["bidding_mode"] = "manual"
        lines.append(f"Max CPM: {strategy['bidding'].get('max_cpm') or 'none'} → {_usd(patch['max_cpm_micros'])}")
    elif args.get("bidding_mode") in ("automatic", "manual"):
        patch["bidding_mode"] = args["bidding_mode"]
    if patch.get("bidding_mode") and patch["bidding_mode"] != strategy["bidding"]["mode"]:
        lines.append(f"Bidding: {strategy['bidding']['mode']} → {patch['bidding_mode']}")
    if not patch:
        return None
    return {"op": "update_strategy", "id": strategy["id"], "patch": patch,
            "diff": f"{strategy['name']}: " + "; ".join(lines)}


async def anthropic_answer(question: str, context: dict, history: list[dict]) -> tuple[str, dict | None]:
    resp = await _client().beta.messages.create(
        model=settings.anthropic_model,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": settings.agent_effort},
        system=SYSTEM_PROMPT,
        tools=[PROPOSE_CHANGE_TOOL],
        messages=_messages(history, context, question),
        betas=[FALLBACK_BETA],
        fallbacks="default",
    )
    if resp.stop_reason == "refusal":
        return REFUSED, None
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
    proposal = None
    for b in resp.content:
        if getattr(b, "type", None) == "tool_use" and b.name == "propose_change":
            proposal = _proposal(dict(b.input or {}), context) or proposal
    if not text and proposal:
        text = "I've prepared that change. Review it below and click **Apply** if it looks right."
    if not text:
        raise RuntimeError(f"empty answer (stop_reason={resp.stop_reason})")
    return text, proposal


async def answer(db: AsyncSession, account_id: uuid.UUID, context: dict, question: str,
                 history: list[dict] | None = None) -> dict:
    """Returns {"text", "proposal", "help"}. "help" is non-empty only when the agent is unavailable."""
    if settings.anthropic_api_key:
        try:
            live = await build_context(db, account_id, context)
            text, proposal = await anthropic_answer(question, live, history or [])
            return {"text": text, "proposal": proposal, "help": []}
        except Exception:  # noqa: BLE001 — any failure shows the notice, never canned facts
            log.exception("agent: Claude call failed")
    return {"text": UNAVAILABLE, "proposal": None, "help": help_for(question, context.get("section"))}


def configured() -> bool:
    return bool(settings.anthropic_api_key)
