"""APScheduler process — enqueues periodic jobs onto the Arq queue.

Periodic jobs (filled in per milestone):
  simulate_tick            every 1 real minute  (= SIM_SPEED simulated minutes)   [M8]
  rollup_hourly            hourly                                                  [M8]
  recompute_recommendations daily                                                 [M10]
  expire_recommendations   daily                                                  [M10]
  run_scheduled_reports    hourly                                                  [M9]
  update_campaign_statuses every 5 minutes                                         [M8]

M0: starts an idle scheduler so `docker compose up` has a healthy process.
"""
from __future__ import annotations

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings


async def delivery_tick() -> None:
    """Same tick the API runs when DELIVERY_LOOP=true; the advisory lock stops both running at once."""
    from app.core.db import SessionLocal
    from app.services import delivery

    async with SessionLocal() as db:
        print(f"[scheduler] delivery tick: {await delivery.tick(db)}")


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(delivery_tick, "interval", seconds=settings.delivery_tick_seconds)
    return scheduler


async def main() -> None:
    scheduler = build_scheduler()
    scheduler.start()
    print(f"[scheduler] {settings.product_name} scheduler online (sim_speed={settings.sim_speed})")
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
