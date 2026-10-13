"""Continuous delivery: the stand-in for a live ad server.

Each tick delivers the *real* time elapsed since the previous tick (times SIM_SPEED), so a
$50/day strategy spends about $50 per real day and every stat lands on its real date. A server
that slept (free hosting) catches the gap up on its next tick, capped at
DELIVERY_MAX_CATCHUP_HOURS. One tick at a time across all processes: a Postgres advisory lock
held on a dedicated connection; a second caller just skips.
"""
from __future__ import annotations

import datetime as dt
import random

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.delivery import SimClock
from app.services import lifecycle
from app.services.simulator import simulate_all

CLOCK = "delivery"
LOCK_KEY = 74_210_001  # arbitrary, app-wide constant for pg_try_advisory_lock


def sim_hours_for(elapsed: dt.timedelta) -> float:
    """Simulated hours to deliver for `elapsed` real time (SIM_SPEED = sim minutes per real minute)."""
    real_h = min(elapsed.total_seconds() / 3600, settings.delivery_max_catchup_hours)
    return max(0.0, real_h) * settings.sim_speed


async def tick(db: AsyncSession, now: dt.datetime | None = None, rng: random.Random | None = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    engine = db.bind  # the AsyncEngine (get_bind() would return the sync one underneath)
    async with engine.connect() as lock_conn:
        if not (await lock_conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": LOCK_KEY})).scalar():
            return {"skipped": "another tick is running"}
        try:
            clock = await db.get(SimClock, CLOCK)
            elapsed = (now - clock.last_tick_at) if clock else dt.timedelta(seconds=settings.delivery_tick_seconds)
            # Advance the clock before delivering: a failure mid-tick skips that window rather than
            # charging it twice on the next tick.
            if clock is None:
                db.add(SimClock(name=CLOCK, last_tick_at=now))
            else:
                clock.last_tick_at = now
            await db.commit()

            moved = await lifecycle.advance(db, now)
            hours = sim_hours_for(elapsed)
            delivered = (
                await simulate_all(db, hours, rng=rng or random.Random())
                if hours > 0 else {"impressions": 0, "spend_micros": 0, "conversions": 0}
            )
            return {"real_hours": round(elapsed.total_seconds() / 3600, 4), "sim_hours": round(hours, 4),
                    "statuses": moved, **delivered}
        finally:
            await lock_conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": LOCK_KEY})


async def backfill(account_id, days: int) -> dict:
    """Admin "simulate N days": `days` of history for one account, then statuses and
    recommendations — the same steps the demo seed runs."""
    from app.services import recommender

    async with SessionLocal() as db:
        delivered = await simulate_all(db, days * 24, rng=random.Random(), account_id=account_id)
        await lifecycle.advance(db, dt.datetime.now(dt.timezone.utc))
        await recommender.generate_for_account(db, account_id)
        return delivered


async def reset_demo(password: str) -> dict:
    from app.services.demo import seed_demo

    async with SessionLocal() as db:
        return await seed_demo(db, password=password)
