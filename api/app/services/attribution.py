"""Attribution engine (docs/08): last-touch view-through within the attribution window.

Set-based: one INSERT … SELECT credits every not-yet-attributed event in the database instead
of loading all events and querying per event in Python (that made each delivery tick take tens
of seconds on a small instance). Semantics are unchanged — see tests/test_attribution_sql.py,
which compares this against the original per-event implementation.

For each event from a known household with a mapped type (page_view→session, lead, purchase,
install) that has no conversion yet:
  1. look back the advertiser's *longest* campaign window (720 h if it has no campaigns);
  2. take the household's latest impression from that advertiser in that span (at or before the event);
  3. credit it only if the event is also inside *that* campaign's own window.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

EVENT_TO_CONVERSION = {"page_view": "session", "lead": "lead", "purchase": "purchase", "install": "install"}
DEFAULT_WINDOW_HOURS = 720

_ATTRIBUTE = text(
    """
    INSERT INTO conversions (event_id, impression_id, account_id, campaign_id, strategy_id, creative_id,
                             channel_id, household_id, ts, event, revenue_micros, lag_seconds, model)
    SELECT e.id, imp.id, imp.account_id, imp.campaign_id, imp.strategy_id, imp.creative_id,
           imp.channel_id, e.household_id, e.ts,
           CASE e.event WHEN 'page_view' THEN 'session' ELSE e.event END,
           COALESCE(e.revenue_micros, 0),
           CAST(FLOOR(EXTRACT(EPOCH FROM (e.ts - imp.ts))) AS INTEGER),  -- truncate, like int(seconds)
           'last_touch'
    FROM events e
    CROSS JOIN LATERAL (
        SELECT COALESCE(MAX(c.attribution_window_hours), :default_window) AS hours
        FROM campaigns c WHERE c.advertiser_id = e.advertiser_id
    ) win
    JOIN LATERAL (
        SELECT i.id, i.ts, i.account_id, i.campaign_id, i.strategy_id, i.creative_id, i.channel_id
        FROM impressions i
        WHERE i.household_id = e.household_id
          AND i.advertiser_id = e.advertiser_id
          AND i.ts <= e.ts
          AND i.ts >= e.ts - make_interval(hours => win.hours)
        ORDER BY i.ts DESC
        LIMIT 1
    ) imp ON TRUE
    JOIN campaigns camp ON camp.id = imp.campaign_id
    WHERE e.household_id IS NOT NULL
      AND e.event IN ('page_view', 'lead', 'purchase', 'install')
      AND NOT EXISTS (SELECT 1 FROM conversions cv WHERE cv.event_id = e.id)
      AND e.ts - imp.ts <= make_interval(hours => camp.attribution_window_hours)
    """
)


async def run_attribution(db: AsyncSession) -> int:
    """Attribute not-yet-attributed events to their last preceding impression. Returns the count."""
    result = await db.execute(_ATTRIBUTE, {"default_window": DEFAULT_WINDOW_HOURS})
    await db.commit()
    return result.rowcount or 0
