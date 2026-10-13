"""Delivery simulator (docs/07) — batch mode for `make simulate HOURS=N`.

Simplified but faithful: for each active strategy it serves impressions up to the
budget at the inventory CPM, picks households (respecting frequency caps and holdouts),
rotates creatives/channels, debits spend, and writes probable outcome *events* (as the
pixel would). Attribution (08) then links events→impressions→conversions.
"""
from __future__ import annotations

import datetime as dt
import math
import random
import uuid

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.models.billing import HoldoutHousehold, TxnType
from app.models.campaign import Campaign, CampaignGoal, CampaignStatus, Strategy, StrategyCreative, StrategyStatus
from app.models.identity import Account
from app.models.inventory import Channel, Household
from app.models.measurement import Impression
from app.models.tracking import Event, EventSource
from app.services.billing import adjust_balance
from app.services.estimator import GOAL_MULTIPLIER, _eligible_sample  # noqa: F401 (reuse goal mult)
from app.services import attribution, rollups

BASE_VISIT_RATE = {
    "awareness": 0.002, "traffic": 0.004, "leads": 0.004, "sales": 0.004,
    "retargeting": 0.012, "app_promotion": 0.0015, "abm": 0.003,
}
VISIT_TO_LEAD = 0.06
VISIT_TO_PURCHASE = 0.025
INSTALL_RATE = 0.0015
AOV_MEAN_USD = 85
MAX_ELIGIBLE = 4000


async def _eligible_ids(db: AsyncSession, strategy: Strategy, campaign: Campaign) -> list:
    conds = []
    loc = strategy.locations or {}
    from app.services.estimator import _LOC_COL

    inc = [i for i in loc.get("include", []) if i.get("type") in _LOC_COL]
    if inc:
        from sqlalchemy import or_

        conds.append(or_(*[_LOC_COL[i["type"]] == i["code"] for i in inc]))
    seg_ids = strategy.interest_segment_ids or []
    if seg_ids:
        from app.models.inventory import InterestSegment

        names = (await db.execute(select(InterestSegment.name).where(InterestSegment.id.in_(seg_ids)))).scalars().all()
        if names:
            conds.append(Household.interests.overlap(list(names)))

    stmt = select(Household.id)
    if conds:
        from sqlalchemy import and_

        stmt = stmt.where(and_(*conds))
    stmt = stmt.order_by(func.random()).limit(MAX_ELIGIBLE)
    ids = (await db.execute(stmt)).scalars().all()
    # exclude holdout
    holdout = set(
        (await db.execute(select(HoldoutHousehold.household_id).where(HoldoutHousehold.campaign_id == campaign.id))).scalars().all()
    )
    return [h for h in ids if h not in holdout]


async def _channels(db: AsyncSession, strategy: Strategy):
    if strategy.placement_mode.value == "selected" and strategy.channel_ids:
        rows = (await db.execute(select(Channel).where(Channel.id.in_(strategy.channel_ids)))).scalars().all()
    else:
        rows = (await db.execute(select(Channel).order_by(Channel.reach_households.desc()).limit(80))).scalars().all()
    return rows or (await db.execute(select(Channel).limit(50))).scalars().all()


async def _creative_ids(db: AsyncSession, strategy: Strategy) -> list:
    return list((await db.execute(select(StrategyCreative.creative_id).where(StrategyCreative.strategy_id == strategy.id))).scalars().all())


def _daily_micros(s: Strategy) -> int:
    if s.budget_type.value == "lifetime" and s.start_date and s.end_date:
        days = max(1, (s.end_date - s.start_date).days + 1)
        return s.budget_micros // days
    return s.budget_micros


async def simulate_strategy(db: AsyncSession, campaign: Campaign, strategy: Strategy, account: Account, hours: int, rng: random.Random):
    eligible = await _eligible_ids(db, strategy, campaign)
    if not eligible:
        return 0, 0
    channels = await _channels(db, strategy)
    if not channels:
        return 0, 0
    creative_ids = await _creative_ids(db, strategy)

    avg_cpm = sum(c.base_cpm_micros * c.reach_households for c in channels) / max(1, sum(c.reach_households for c in channels))
    avg_cpm *= GOAL_MULTIPLIER.get(campaign.goal, 1.0)

    target_spend = _daily_micros(strategy) * hours / 24
    target_spend = min(target_spend, max(0, account.balance_micros))
    if target_spend <= 0 or avg_cpm <= 0:
        return 0, 0
    exact = target_spend / avg_cpm * 1000
    # Short delivery ticks need fractions of an impression; round stochastically so they add up
    # (flooring lost ~25% of spend at 5-minute ticks).
    n_imps = int(exact) + (1 if rng.random() < exact - int(exact) else 0)

    fc = strategy.frequency_cap or {}
    per_day = fc.get("impressions") if fc else None
    days = max(1, hours / 24)
    cap_total = int(per_day * days) if per_day else 10 ** 9

    ch_weights = [c.reach_households for c in channels]
    now = dt.datetime.now(dt.timezone.utc)
    window_start = now - dt.timedelta(hours=hours)
    base_rate = BASE_VISIT_RATE.get(campaign.goal.value, 0.004)

    imp_rows = []
    event_rows = []
    hh_count: dict = {}
    spend = 0
    served = 0
    attempts = 0
    while served < n_imps and attempts < n_imps * 3:
        attempts += 1
        hh = eligible[rng.randrange(len(eligible))]
        if hh_count.get(hh, 0) >= cap_total:
            continue
        ch = rng.choices(channels, weights=ch_weights, k=1)[0]
        cre = rng.choice(creative_ids) if creative_ids else None
        ts = window_start + dt.timedelta(seconds=rng.uniform(0, hours * 3600))
        cost = int(ch.base_cpm_micros * GOAL_MULTIPLIER.get(campaign.goal, 1.0) / 1000 * rng.uniform(0.9, 1.1))
        live_sport = ch.category.value == "sports" and 19 <= ts.hour <= 23
        imp_rows.append({
            "ts": ts, "account_id": account.id, "campaign_id": campaign.id, "strategy_id": strategy.id,
            "creative_id": cre, "channel_id": ch.id, "household_id": hh, "advertiser_id": campaign.advertiser_id,
            "device_type": "tv", "cost_micros": cost, "live_sport": live_sport,
        })
        spend += cost
        hh_count[hh] = hh_count.get(hh, 0) + 1
        served += 1

        # probable outcome event (written as the pixel would)
        mult = 1.0
        if 19 <= ts.hour <= 23:
            mult *= 1.2
        if rng.random() < base_rate * mult:
            lag = min(30 * 86400, int(rng.expovariate(1 / (26 * 3600))))
            ev_ts = ts + dt.timedelta(seconds=lag)
            ev, rev = "page_view", 0
            if campaign.goal == CampaignGoal.sales and rng.random() < VISIT_TO_PURCHASE:
                ev, rev = "purchase", int(rng.lognormvariate(math.log(AOV_MEAN_USD), 0.6) * 1_000_000)
            elif campaign.goal == CampaignGoal.leads and rng.random() < VISIT_TO_LEAD:
                ev = "lead"
            elif campaign.goal == CampaignGoal.app_promotion:
                continue
            event_rows.append({
                "ts": ev_ts, "account_id": account.id, "advertiser_id": campaign.advertiser_id,
                "source": EventSource.pixel, "event": ev, "household_id": hh, "ip_hash": None,
                "revenue_micros": rev, "order_id": None, "url": None, "user_agent": None,
                "lm_id": None, "raw": {},
            })
        elif campaign.goal == CampaignGoal.app_promotion and rng.random() < INSTALL_RATE:
            event_rows.append({
                "ts": ts + dt.timedelta(hours=1), "account_id": account.id, "advertiser_id": campaign.advertiser_id,
                "source": EventSource.mmp, "event": "install", "household_id": hh, "ip_hash": None,
                "revenue_micros": 0, "order_id": None, "url": None, "user_agent": None, "lm_id": None, "raw": {},
            })

    if imp_rows:
        await db.execute(insert(Impression), imp_rows)
    if event_rows:
        await db.execute(insert(Event), event_rows)
    if spend > 0:
        await adjust_balance(db, account, -spend, TxnType.spend, {"campaign_id": str(campaign.id)})
    await db.commit()
    return served, spend


async def simulate_all(
    db: AsyncSession,
    hours: float,
    *,
    rng: random.Random | None = None,
    account_id: uuid.UUID | None = None,
) -> dict:
    """Deliver `hours` of activity ending now for every live campaign (or one account's).

    `rng` defaults to a fixed seed so batch runs and tests are reproducible; the continuous
    delivery loop passes a fresh one, otherwise every tick would replay identical randomness.
    """
    rng = rng or random.Random(42)
    q = select(Campaign).where(Campaign.status.in_([CampaignStatus.learning, CampaignStatus.delivering]))
    if account_id is not None:
        q = q.where(Campaign.account_id == account_id)
    campaigns = (await db.execute(q)).scalars().all()
    total_imps = total_spend = 0
    for c in campaigns:
        account = await db.get(Account, c.account_id)
        strategies = (
            await db.execute(select(Strategy).where(Strategy.campaign_id == c.id, Strategy.status == StrategyStatus.active))
        ).scalars().all()
        for s in strategies:
            imps, spend = await simulate_strategy(db, c, s, account, hours, rng)
            total_imps += imps
            total_spend += spend
    n_conv = await attribution.run_attribution(db)
    await rollups.rebuild_rollups(db)
    return {"campaigns": len(campaigns), "impressions": total_imps, "spend_micros": total_spend, "conversions": n_conv}


async def simulate(hours: int = 24) -> dict:
    async with SessionLocal() as db:
        return await simulate_all(db, hours)
