"""Campaign status transitions that depend on the calendar, run on every delivery tick.

  scheduled  -> learning    once the earliest active strategy's start date arrives
  learning   -> delivering  once `learning_until` has passed
  live       -> completed   once every active strategy's end date is in the past

Publishing set these states but nothing ever advanced them: scheduled campaigns never started
and every campaign stayed in Learning forever.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, CampaignStatus, Strategy, StrategyStatus
from app.services.publish import LEARNING_DAYS

LIVE = (CampaignStatus.learning, CampaignStatus.delivering)


async def advance(db: AsyncSession, now: dt.datetime) -> dict[str, int]:
    today = now.date()
    moved = {"started": 0, "out_of_learning": 0, "completed": 0}
    campaigns = (
        await db.execute(select(Campaign).where(Campaign.status.in_([CampaignStatus.scheduled, *LIVE])))
    ).scalars().all()
    for c in campaigns:
        strategies = (
            await db.execute(select(Strategy).where(Strategy.campaign_id == c.id, Strategy.status == StrategyStatus.active))
        ).scalars().all()
        if not strategies:
            continue
        if c.status == CampaignStatus.scheduled:
            starts = [s.start_date for s in strategies if s.start_date]
            if not starts or min(starts) <= today:
                c.status = CampaignStatus.learning
                c.learning_until = now + dt.timedelta(days=LEARNING_DAYS)
                moved["started"] += 1
            continue
        ends = [s.end_date for s in strategies]
        if all(e is not None and e < today for e in ends):
            c.status = CampaignStatus.completed
            for s in strategies:
                s.status = StrategyStatus.completed
            moved["completed"] += 1
            continue
        if c.status == CampaignStatus.learning and c.learning_until and c.learning_until <= now:
            c.status = CampaignStatus.delivering
            moved["out_of_learning"] += 1
    await db.commit()
    return moved
