# Original ORM-based rollups (pre set-based rewrite), kept only as the reference for
# tests/test_attribution_sql.py. Not used by the app.
"""Daily rollups (docs/11): aggregate impressions + conversions into stats_daily.

Additive metrics (impressions, spend, sessions, leads, purchases, installs, revenue)
SUM correctly across rows; household reach (distinct) is queried directly where needed.
"""
from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.inventory import Household
from app.models.measurement import Conversion, Impression, StatsDaily


async def rebuild_rollups(db: AsyncSession) -> None:
    await db.execute(delete(StatsDaily))

    # impression aggregates (state via household join)
    imp_q = (
        select(
            func.date(Impression.ts).label("date"),
            Impression.account_id, Impression.advertiser_id, Impression.campaign_id,
            Impression.strategy_id, Impression.creative_id, Impression.channel_id, Household.state,
            func.count().label("impressions"),
            func.count(func.distinct(Impression.household_id)).label("households_reached"),
            func.sum(Impression.cost_micros).label("spend_micros"),
        )
        .join(Household, Household.id == Impression.household_id)
        .group_by(
            func.date(Impression.ts), Impression.account_id, Impression.advertiser_id, Impression.campaign_id,
            Impression.strategy_id, Impression.creative_id, Impression.channel_id, Household.state,
        )
    )
    for r in (await db.execute(imp_q)).all():
        db.add(StatsDaily(
            date=r.date, account_id=r.account_id, advertiser_id=r.advertiser_id, campaign_id=r.campaign_id,
            strategy_id=r.strategy_id, creative_id=r.creative_id, channel_id=r.channel_id, state=r.state,
            impressions=r.impressions, households_reached=r.households_reached, spend_micros=r.spend_micros or 0,
        ))

    # conversion aggregates (separate rows; additive metrics SUM correctly)
    conv_q = (
        select(
            func.date(Conversion.ts).label("date"),
            Conversion.account_id, Conversion.campaign_id, Conversion.strategy_id,
            Conversion.creative_id, Conversion.channel_id, Conversion.event, Household.state,
            func.count().label("n"), func.sum(Conversion.revenue_micros).label("revenue"),
        )
        .join(Household, Household.id == Conversion.household_id, isouter=True)
        .group_by(
            func.date(Conversion.ts), Conversion.account_id, Conversion.campaign_id, Conversion.strategy_id,
            Conversion.creative_id, Conversion.channel_id, Conversion.event, Household.state,
        )
    )
    adv_cache: dict = {}
    for r in (await db.execute(conv_q)).all():
        adv = adv_cache.get(r.campaign_id)
        if adv is None:
            camp = await db.get(Campaign, r.campaign_id)
            adv = camp.advertiser_id if camp else None
            adv_cache[r.campaign_id] = adv
        row = StatsDaily(
            date=r.date, account_id=r.account_id, advertiser_id=adv, campaign_id=r.campaign_id,
            strategy_id=r.strategy_id, creative_id=r.creative_id, channel_id=r.channel_id, state=r.state,
            revenue_micros=r.revenue or 0,
            sessions=r.n if r.event == "session" else 0,
            leads=r.n if r.event == "lead" else 0,
            purchases=r.n if r.event == "purchase" else 0,
            installs=r.n if r.event == "install" else 0,
        )
        db.add(row)

    await db.commit()
