"""Daily rollups (docs/11): aggregate impressions + conversions into stats_daily.

Additive metrics (impressions, spend, sessions, leads, purchases, installs, revenue)
SUM correctly across rows; household reach (distinct) is queried directly where needed.

Set-based: two INSERT … SELECT statements run inside Postgres. The previous version built every
aggregate row as an ORM object in Python, which was too slow to run on every delivery tick.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Impression aggregates (state via household join).
_IMPRESSIONS = text(
    """
    INSERT INTO stats_daily (date, account_id, advertiser_id, campaign_id, strategy_id, creative_id,
                             channel_id, state, impressions, households_reached, spend_micros,
                             sessions, leads, purchases, installs, revenue_micros)
    SELECT CAST(i.ts AS DATE), i.account_id, i.advertiser_id, i.campaign_id, i.strategy_id, i.creative_id,
           i.channel_id, h.state, COUNT(*), COUNT(DISTINCT i.household_id), COALESCE(SUM(i.cost_micros), 0),
           0, 0, 0, 0, 0
    FROM impressions i
    JOIN households h ON h.id = i.household_id
    GROUP BY CAST(i.ts AS DATE), i.account_id, i.advertiser_id, i.campaign_id, i.strategy_id,
             i.creative_id, i.channel_id, h.state
    """
)

# Conversion aggregates — separate rows so additive metrics still SUM correctly.
_CONVERSIONS = text(
    """
    INSERT INTO stats_daily (date, account_id, advertiser_id, campaign_id, strategy_id, creative_id,
                             channel_id, state, impressions, households_reached, spend_micros,
                             sessions, leads, purchases, installs, revenue_micros)
    SELECT CAST(cv.ts AS DATE), cv.account_id, camp.advertiser_id, cv.campaign_id, cv.strategy_id,
           cv.creative_id, cv.channel_id, h.state, 0, 0, 0,
           SUM(CASE WHEN cv.event = 'session'  THEN 1 ELSE 0 END),
           SUM(CASE WHEN cv.event = 'lead'     THEN 1 ELSE 0 END),
           SUM(CASE WHEN cv.event = 'purchase' THEN 1 ELSE 0 END),
           SUM(CASE WHEN cv.event = 'install'  THEN 1 ELSE 0 END),
           COALESCE(SUM(cv.revenue_micros), 0)
    FROM conversions cv
    JOIN campaigns camp ON camp.id = cv.campaign_id
    LEFT JOIN households h ON h.id = cv.household_id
    GROUP BY CAST(cv.ts AS DATE), cv.account_id, camp.advertiser_id, cv.campaign_id, cv.strategy_id,
             cv.creative_id, cv.channel_id, cv.event, h.state
    """
)


async def rebuild_rollups(db: AsyncSession) -> None:
    await db.execute(text("DELETE FROM stats_daily"))
    await db.execute(_IMPRESSIONS)
    await db.execute(_CONVERSIONS)
    await db.commit()
