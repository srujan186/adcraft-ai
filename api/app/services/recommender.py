"""Elasticity fit, performance forecaster, and data-driven recommendations (docs/09)."""
from __future__ import annotations

import datetime as dt
import math

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, CampaignGoal, CampaignStatus, Strategy
from app.models.intelligence import (
    Elasticity,
    Recommendation,
    RecommendationStatus,
    RecommendationSuppression,
    RecommendationType,
)
from app.models.measurement import StatsDaily

OUTCOME_METRIC = {
    "traffic": "sessions", "leads": "sessions", "retargeting": "sessions",
    "sales": "purchases", "app_promotion": "installs", "awareness": "impressions", "abm": "sessions",
}
DEFAULT_BETA = 0.6
MIN_DAYS = 7
PERMANENT_REASONS = {"purpose", "on_purpose", "manual bidding on purpose", "My targeting is narrow on purpose", "I use manual bidding on purpose"}


def _outcome_col(goal: str):
    m = OUTCOME_METRIC.get(goal, "sessions")
    return {"sessions": StatsDaily.sessions, "purchases": StatsDaily.purchases,
            "installs": StatsDaily.installs, "impressions": StatsDaily.impressions}[m]


async def _daily_points(db: AsyncSession, advertiser_id, goal: str) -> list[tuple[float, float]]:
    oc = _outcome_col(goal)
    rows = (
        await db.execute(
            select(StatsDaily.date, func.sum(StatsDaily.spend_micros), func.sum(oc))
            .where(StatsDaily.advertiser_id == advertiser_id)
            .group_by(StatsDaily.date).order_by(StatsDaily.date)
        )
    ).all()
    return [(float(r[1] or 0) / 1e6, float(r[2] or 0)) for r in rows if (r[1] or 0) > 0 and (r[2] or 0) > 0]


def _fit(points: list[tuple[float, float]]) -> tuple[float, float, float, int]:
    """log-log OLS: outcome = alpha * spend^beta. Falls back to a prior when degenerate."""
    n = len(points)
    xs = [math.log(s) for s, _ in points]
    ys = [math.log(o) for _, o in points]
    if n >= 14 and (max(xs) - min(xs)) > 0.15:
        mx, my = sum(xs) / n, sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        beta = sxy / sxx if sxx else DEFAULT_BETA
        alpha = math.exp(my - beta * mx)
        ss_res = sum((y - (math.log(alpha) + beta * x)) ** 2 for x, y in zip(xs, ys))
        ss_tot = sum((y - my) ** 2 for y in ys)
        r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
        beta = min(1.0, max(0.1, beta))
        if r2 >= 0.5:
            return alpha, beta, r2, n
    # prior fallback anchored to the mean point
    if n:
        ms = sum(s for s, _ in points) / n
        mo = sum(o for _, o in points) / n
        alpha = mo / (ms ** DEFAULT_BETA) if ms > 0 else 1.0
        return alpha, DEFAULT_BETA, 0.6, n
    return 1.0, DEFAULT_BETA, 0.0, 0


async def fit_elasticity(db: AsyncSession, advertiser_id, goal: str) -> Elasticity:
    points = await _daily_points(db, advertiser_id, goal)
    alpha, beta, r2, n = _fit(points)
    row = (
        await db.execute(select(Elasticity).where(Elasticity.advertiser_id == advertiser_id, Elasticity.goal == goal))
    ).scalar_one_or_none()
    if row is None:
        row = Elasticity(advertiser_id=advertiser_id, goal=goal, alpha=alpha, beta=beta, r2=r2, n_days=n)
        db.add(row)
    else:
        row.alpha, row.beta, row.r2, row.n_days = alpha, beta, r2, n
    await db.commit()
    await db.refresh(row)
    return row


async def forecast(db: AsyncSession, strategy: Strategy) -> dict | None:
    campaign = await db.get(Campaign, strategy.campaign_id)
    if campaign is None:
        return None
    el = await fit_elasticity(db, campaign.advertiser_id, campaign.goal.value)
    beta = float(el.beta)

    oc = _outcome_col(campaign.goal.value)
    days = (
        await db.execute(
            select(func.count(func.distinct(StatsDaily.date)), func.sum(StatsDaily.spend_micros), func.sum(oc))
            .where(StatsDaily.account_id == strategy.account_id, StatsDaily.campaign_id == campaign.id)
        )
    ).one()
    n_days = int(days[0] or 0)
    if n_days < MIN_DAYS:
        return None
    cur_budget = strategy.budget_micros / 1e6
    avg_spend = float(days[1] or 0) / 1e6 / max(1, n_days)
    avg_outcome = float(days[2] or 0) / max(1, n_days)
    base = avg_spend if avg_spend > 0 else cur_budget
    alpha_s = avg_outcome / (base ** beta) if base > 0 else 0.0

    b_rec = min(cur_budget * 3, cur_budget * (0.7 ** (1 / (beta - 1)))) if beta < 1 else cur_budget * 3
    b_rec = max(b_rec, cur_budget)

    points = []
    for i in range(40):
        b = cur_budget * (0.25 + (4 - 0.25) * i / 39)
        points.append({"budget_micros": int(b * 1e6), "outcome": round(alpha_s * (b ** beta), 1)})

    return {
        "outcome_metric": OUTCOME_METRIC.get(campaign.goal.value, "sessions"),
        "current_budget_micros": int(cur_budget * 1e6),
        "recommended_budget_micros": int(b_rec * 1e6),
        "current_outcome": round(alpha_s * (base ** beta), 1),
        "recommended_outcome": round(alpha_s * (b_rec ** beta), 1),
        "beta": beta, "points": points,
    }


async def _suppressed(db: AsyncSession, account_id, campaign_id, rtype: RecommendationType) -> bool:
    now = dt.datetime.now(dt.timezone.utc)
    rows = (
        await db.execute(
            select(RecommendationSuppression).where(
                RecommendationSuppression.account_id == account_id, RecommendationSuppression.type == rtype
            )
        )
    ).scalars().all()
    for s in rows:
        if s.campaign_id in (None, campaign_id) and (s.until is None or s.until > now):
            return True
    return False


async def generate_for_account(db: AsyncSession, account_id) -> int:
    campaigns = (
        await db.execute(
            select(Campaign).where(Campaign.account_id == account_id, Campaign.status.in_([CampaignStatus.learning, CampaignStatus.delivering]))
        )
    ).scalars().all()
    created = 0
    for c in campaigns:
        # need >= 7 *delivery* days (days with spend); future-dated conversion-only
        # rows from attribution lag must not satisfy this on their own.
        day_rows = (
            await db.execute(
                select(StatsDaily.date)
                .where(StatsDaily.campaign_id == c.id)
                .group_by(StatsDaily.date)
                .having(func.sum(StatsDaily.spend_micros) > 0)
            )
        ).all()
        if len(day_rows) < MIN_DAYS:
            continue
        strategies = (await db.execute(select(Strategy).where(Strategy.campaign_id == c.id))).scalars().all()
        for s in strategies:
            created += await _maybe_increase_budget(db, c, s)
            created += await _maybe_extend_window(db, c)
    await db.commit()
    return created


async def _has_open(db, campaign_id, strategy_id, rtype) -> bool:
    q = select(func.count()).select_from(Recommendation).where(
        Recommendation.campaign_id == campaign_id, Recommendation.type == rtype,
        Recommendation.status == RecommendationStatus.open,
    )
    if strategy_id:
        q = q.where(Recommendation.strategy_id == strategy_id)
    return (await db.execute(q)).scalar_one() > 0


async def _maybe_increase_budget(db: AsyncSession, c: Campaign, s: Strategy) -> int:
    if await _suppressed(db, c.account_id, c.id, RecommendationType.increase_budget):
        return 0
    if await _has_open(db, c.id, s.id, RecommendationType.increase_budget):
        return 0
    # spends >= 95% of daily budget on >= 5 of the last 7 *delivery* days.
    # Only days with spend count: attribution lag writes future-dated, spend-free
    # stats_daily rows for conversions, and those must not displace real delivery days.
    rows = (
        await db.execute(
            select(StatsDaily.date, func.sum(StatsDaily.spend_micros))
            .where(StatsDaily.campaign_id == c.id, StatsDaily.strategy_id == s.id)
            .group_by(StatsDaily.date)
            .having(func.sum(StatsDaily.spend_micros) > 0)
            .order_by(StatsDaily.date.desc()).limit(7)
        )
    ).all()
    capped_days = sum(1 for _, spend in rows if (spend or 0) >= 0.95 * s.budget_micros)
    if capped_days < 5:
        return 0
    fc = await forecast(db, s)
    if fc is None or fc["recommended_budget_micros"] <= s.budget_micros:
        return 0
    uplift = round((fc["recommended_outcome"] / fc["current_outcome"] - 1) * 100) if fc["current_outcome"] else 0
    db.add(Recommendation(
        account_id=c.account_id, campaign_id=c.id, strategy_id=s.id, type=RecommendationType.increase_budget,
        title=f"Increase budget on '{s.name}'",
        body=f"This strategy spends its full budget most days. Scaling to ${fc['recommended_budget_micros']/1e6:,.0f}/day is projected to grow {fc['outcome_metric']}.",
        projected={"metric": fc["outcome_metric"], "current": fc["current_outcome"], "projected": fc["recommended_outcome"], "uplift_pct": uplift},
        action={"op": "update_strategy", "id": str(s.id), "patch": {"budget_micros": fc["recommended_budget_micros"]}},
        expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=90),
    ))
    return 1


async def _maybe_extend_window(db: AsyncSession, c: Campaign) -> int:
    if c.goal not in (CampaignGoal.sales, CampaignGoal.leads) or c.attribution_window_hours >= 168:
        return 0
    if await _suppressed(db, c.account_id, c.id, RecommendationType.extend_attribution_window):
        return 0
    if await _has_open(db, c.id, None, RecommendationType.extend_attribution_window):
        return 0
    db.add(Recommendation(
        account_id=c.account_id, campaign_id=c.id, strategy_id=None, type=RecommendationType.extend_attribution_window,
        title="Extend your attribution window",
        body="Sales and leads often convert days after a TV impression. Extending to 30 days will capture more conversions.",
        projected={"metric": "conversions", "uplift_pct": 15},
        action={"op": "update_campaign", "id": str(c.id), "patch": {"attribution_window_hours": 720}},
        expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=90),
    ))
    return 1


SUPPRESS_DAYS = {"not_now": 30, "Not now": 30}


async def apply_recommendation(db: AsyncSession, rec: Recommendation) -> None:
    action = rec.action or {}
    if action.get("op") == "update_strategy":
        s = await db.get(Strategy, action["id"])
        if s:
            for k, v in action["patch"].items():
                setattr(s, k, v)
    elif action.get("op") == "update_campaign":
        c = await db.get(Campaign, action["id"])
        if c:
            for k, v in action["patch"].items():
                setattr(c, k, v)
    rec.status = RecommendationStatus.applied
    await db.commit()


async def reject_recommendation(db: AsyncSession, rec: Recommendation, reason_code: str, note: str | None) -> None:
    rec.status = RecommendationStatus.rejected
    rec.reject_reason = reason_code
    rec.reject_note = note
    permanent = any(p.lower() in (reason_code or "").lower() for p in ["purpose"])
    until = None if permanent else dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=SUPPRESS_DAYS.get(reason_code, 60))
    db.add(RecommendationSuppression(account_id=rec.account_id, campaign_id=rec.campaign_id, type=rec.type, until=until))
    await db.commit()
