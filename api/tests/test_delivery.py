"""P0-1: continuous delivery tick + calendar-driven campaign statuses."""
import asyncio
import datetime as dt
import random

import pytest
from sqlalchemy import func, select, text, update

from app.core.config import settings
from app.models.campaign import Campaign, CampaignStatus, Strategy, StrategyStatus
from app.models.delivery import SimClock
from app.models.identity import Account
from app.models.inventory import Channel, ChannelCategory, Household
from app.models.measurement import Impression
from app.services import delivery, lifecycle
from tests.conftest import TestSessionLocal, engine, signup

DAILY = 50_000_000  # $50/day
NOW = dt.datetime(2026, 10, 13, 12, 0, tzinfo=dt.timezone.utc)


def _live_campaign(client, status=CampaignStatus.learning, **strategy_values) -> str:
    h = signup(client, f"dl{random.randint(0, 10**9)}@acme.io", "Acme")["headers"]
    adv = client.post("/api/v1/advertisers", headers=h, json={
        "name": "Nimbus", "industry": "ecommerce", "timezone": "America/New_York"}).json()["id"]
    cid = client.post("/api/v1/campaigns", headers=h, json={
        "advertiser_id": adv, "name": "Live", "goal": "traffic", "kpi": "cps"}).json()["id"]

    async def go():
        async with TestSessionLocal() as db:
            if not (await db.execute(select(func.count()).select_from(Household))).scalar_one():
                db.add_all([Household(
                    ip_hash=f"d{i}", zip=f"Z{i:05d}", dma_code="500", state="CA", city="X", county="X",
                    congressional_district="CA-01", timezone="America/Los_Angeles", age_bucket="25-34",
                    gender="female", income_bucket="50k-99k", education="bachelors", family="no_children",
                    homeowner=True, interests=["Shopping"], device_types=["tv"], propensity_x100=100)
                    for i in range(150)])
                db.add_all([Channel(name=f"C{i}", category=ChannelCategory.entertainment,
                                    reach_households=10_000_000, base_cpm_micros=20_000_000) for i in range(5)])
            await db.execute(update(Account).values(balance_micros=100_000_000_000))
            await db.execute(update(Campaign).where(Campaign.id == cid).values(
                status=status, learning_until=NOW + dt.timedelta(days=14)))
            await db.execute(update(Strategy).where(Strategy.campaign_id == cid).values(
                status=StrategyStatus.active, budget_micros=DAILY, **strategy_values))
            await db.commit()
    asyncio.run(go())
    return cid


def _set_clock(last_tick_at):
    async def go():
        async with TestSessionLocal() as db:
            await db.merge(SimClock(name=delivery.CLOCK, last_tick_at=last_tick_at))
            await db.commit()
    asyncio.run(go())


def _tick(now):
    async def go():
        async with TestSessionLocal() as db:
            return await delivery.tick(db, now=now, rng=random.Random(5))
    return asyncio.run(go())


def _spend(cid):
    async def go():
        async with TestSessionLocal() as db:
            return int((await db.execute(select(func.coalesce(func.sum(Impression.cost_micros), 0))
                                         .where(Impression.campaign_id == cid))).scalar_one())
    return asyncio.run(go())


@pytest.fixture()
def realtime(monkeypatch):
    monkeypatch.setattr(settings, "sim_speed", 1.0)
    monkeypatch.setattr(settings, "delivery_max_catchup_hours", 48.0)


def test_a_day_of_real_time_spends_about_a_days_budget(client, realtime):
    cid = _live_campaign(client)
    _set_clock(NOW - dt.timedelta(hours=24))
    r = _tick(NOW)
    assert r["sim_hours"] == pytest.approx(24)
    assert _spend(cid) == pytest.approx(DAILY, rel=0.10)

    async def clock():
        async with TestSessionLocal() as db:
            return (await db.get(SimClock, delivery.CLOCK)).last_tick_at
    assert asyncio.run(clock()) == NOW


def test_catch_up_after_sleeping_is_capped(client, realtime):
    cid = _live_campaign(client)
    _set_clock(NOW - dt.timedelta(days=10))
    assert _tick(NOW)["sim_hours"] == pytest.approx(48)
    assert _spend(cid) == pytest.approx(2 * DAILY, rel=0.10)


def test_an_immediate_second_tick_delivers_nothing_more(client, realtime):
    cid = _live_campaign(client)
    _set_clock(NOW - dt.timedelta(hours=6))
    _tick(NOW)
    first = _spend(cid)
    assert _tick(NOW)["sim_hours"] == 0
    assert _spend(cid) == first


def test_sim_speed_accelerates_delivery(client, monkeypatch):
    monkeypatch.setattr(settings, "sim_speed", 60.0)
    cid = _live_campaign(client)
    _set_clock(NOW - dt.timedelta(hours=1))
    assert _tick(NOW)["sim_hours"] == pytest.approx(60)
    assert _spend(cid) == pytest.approx(DAILY * 60 / 24, rel=0.10)


def test_tick_skips_while_another_holds_the_lock(client, realtime):
    _live_campaign(client)
    _set_clock(NOW - dt.timedelta(hours=1))

    async def go():
        async with engine.connect() as other:
            assert (await other.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": delivery.LOCK_KEY})).scalar()
            try:
                async with TestSessionLocal() as db:
                    return await delivery.tick(db, now=NOW)
            finally:
                await other.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": delivery.LOCK_KEY})
    assert "skipped" in asyncio.run(go())


def _status(cid):
    async def go():
        async with TestSessionLocal() as db:
            c = await db.get(Campaign, cid)
            return c.status, c.learning_until
    return asyncio.run(go())


def _advance(now):
    async def go():
        async with TestSessionLocal() as db:
            return await lifecycle.advance(db, now)
    return asyncio.run(go())


def test_scheduled_campaign_starts_on_its_start_date(client):
    cid = _live_campaign(client, status=CampaignStatus.scheduled, start_date=NOW.date() + dt.timedelta(days=2))
    _advance(NOW)
    assert _status(cid)[0] == CampaignStatus.scheduled
    _advance(NOW + dt.timedelta(days=2))
    status, until = _status(cid)
    assert status == CampaignStatus.learning
    assert until == NOW + dt.timedelta(days=2) + dt.timedelta(days=14)


def test_learning_ends_when_learning_until_passes(client):
    cid = _live_campaign(client)
    _advance(NOW + dt.timedelta(days=13))
    assert _status(cid)[0] == CampaignStatus.learning
    _advance(NOW + dt.timedelta(days=14))
    assert _status(cid)[0] == CampaignStatus.delivering


def test_campaign_completes_after_its_end_date(client):
    cid = _live_campaign(client, end_date=NOW.date())
    _advance(NOW)
    assert _status(cid)[0] == CampaignStatus.learning  # ends today: still running
    _advance(NOW + dt.timedelta(days=1))
    assert _status(cid)[0] == CampaignStatus.completed
