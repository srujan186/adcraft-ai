"""Attribution engine (docs/08): last-touch view-through within the attribution window."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.measurement import Conversion, Impression
from app.models.tracking import Event

EVENT_TO_CONVERSION = {"page_view": "session", "lead": "lead", "purchase": "purchase", "install": "install"}
DEFAULT_WINDOW_HOURS = 720


async def run_attribution(db: AsyncSession) -> int:
    """Attribute not-yet-attributed events to their last preceding impression."""
    attributed = set((await db.execute(select(Conversion.event_id).where(Conversion.event_id.isnot(None)))).scalars().all())
    events = (
        await db.execute(select(Event).where(Event.household_id.isnot(None)).order_by(Event.ts))
    ).scalars().all()

    # cache per-advertiser max window
    win_cache: dict = {}
    count = 0
    for e in events:
        if e.id in attributed:
            continue
        conv_event = EVENT_TO_CONVERSION.get(e.event)
        if conv_event is None:
            continue

        win_h = win_cache.get(e.advertiser_id)
        if win_h is None:
            rows = (
                await db.execute(select(Campaign.attribution_window_hours).where(Campaign.advertiser_id == e.advertiser_id))
            ).scalars().all()
            win_h = max(rows) if rows else DEFAULT_WINDOW_HOURS
            win_cache[e.advertiser_id] = win_h

        lo = e.ts - dt.timedelta(hours=win_h)
        imp = (
            await db.execute(
                select(Impression)
                .where(
                    Impression.household_id == e.household_id,
                    Impression.advertiser_id == e.advertiser_id,
                    Impression.ts <= e.ts,
                    Impression.ts >= lo,
                )
                .order_by(Impression.ts.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if imp is None:
            continue

        camp = await db.get(Campaign, imp.campaign_id)
        if camp and (e.ts - imp.ts) > dt.timedelta(hours=camp.attribution_window_hours):
            continue

        db.add(Conversion(
            event_id=e.id, impression_id=imp.id, account_id=imp.account_id, campaign_id=imp.campaign_id,
            strategy_id=imp.strategy_id, creative_id=imp.creative_id, channel_id=imp.channel_id,
            household_id=e.household_id, ts=e.ts, event=conv_event, revenue_micros=e.revenue_micros,
            lag_seconds=int((e.ts - imp.ts).total_seconds()), model="last_touch",
        ))
        count += 1

    await db.commit()
    return count
