"""The set-based attribution/rollups must produce exactly what the original per-event Python
implementation produced. The originals are kept as references (here, and tests/_rollups_reference.py)."""
import asyncio
import datetime as dt
import random

from sqlalchemy import delete, func, select, update

from app.models.campaign import Campaign, CampaignStatus, Strategy, StrategyStatus
from app.models.identity import Account
from app.models.inventory import Channel, ChannelCategory, Household
from app.models.measurement import Conversion, Impression, StatsDaily
from app.models.tracking import Event, EventSource
from app.services import attribution, rollups
from app.services.simulator import simulate_all
from tests import _rollups_reference
from tests.conftest import TestSessionLocal, signup

EVENT_TO_CONVERSION = attribution.EVENT_TO_CONVERSION


async def _reference_attribution(db) -> int:
    """The original implementation (pre-rewrite), unchanged in logic."""
    attributed = set((await db.execute(select(Conversion.event_id).where(Conversion.event_id.isnot(None)))).scalars().all())
    events = (await db.execute(select(Event).where(Event.household_id.isnot(None)).order_by(Event.ts))).scalars().all()
    win_cache, count = {}, 0
    for e in events:
        if e.id in attributed:
            continue
        conv_event = EVENT_TO_CONVERSION.get(e.event)
        if conv_event is None:
            continue
        win_h = win_cache.get(e.advertiser_id)
        if win_h is None:
            rows = (await db.execute(select(Campaign.attribution_window_hours)
                                     .where(Campaign.advertiser_id == e.advertiser_id))).scalars().all()
            win_h = max(rows) if rows else attribution.DEFAULT_WINDOW_HOURS
            win_cache[e.advertiser_id] = win_h
        lo = e.ts - dt.timedelta(hours=win_h)
        imp = (await db.execute(select(Impression).where(
            Impression.household_id == e.household_id, Impression.advertiser_id == e.advertiser_id,
            Impression.ts <= e.ts, Impression.ts >= lo).order_by(Impression.ts.desc()).limit(1))).scalar_one_or_none()
        if imp is None:
            continue
        camp = await db.get(Campaign, imp.campaign_id)
        if camp and (e.ts - imp.ts) > dt.timedelta(hours=camp.attribution_window_hours):
            continue
        db.add(Conversion(event_id=e.id, impression_id=imp.id, account_id=imp.account_id, campaign_id=imp.campaign_id,
                          strategy_id=imp.strategy_id, creative_id=imp.creative_id, channel_id=imp.channel_id,
                          household_id=e.household_id, ts=e.ts, event=conv_event, revenue_micros=e.revenue_micros,
                          lag_seconds=int((e.ts - imp.ts).total_seconds()), model="last_touch"))
        count += 1
    await db.commit()
    return count


def _setup(client):
    """Two campaigns (720 h and 24 h windows), two weeks of simulated delivery, plus edge cases."""
    h = signup(client, "attr@acme.io", "Acme")["headers"]
    adv = client.post("/api/v1/advertisers", headers=h, json={
        "name": "Nimbus", "industry": "ecommerce", "timezone": "America/New_York"}).json()["id"]
    long_c = client.post("/api/v1/campaigns", headers=h, json={
        "advertiser_id": adv, "name": "Long window", "goal": "sales", "kpi": "cpp"}).json()["id"]
    short_c = client.post("/api/v1/campaigns", headers=h, json={
        "advertiser_id": adv, "name": "Short window", "goal": "sales", "kpi": "cpp"}).json()["id"]

    async def go():
        async with TestSessionLocal() as db:
            rnd = random.Random(3)
            db.add_all([Household(
                ip_hash=f"a{i}", zip=f"Z{i:05d}", dma_code="500", state=rnd.choice(["CA", "NY", "TX"]), city="X",
                county="X", congressional_district="CA-01", timezone="America/Los_Angeles", age_bucket="25-34",
                gender="female", income_bucket="50k-99k", education="bachelors", family="no_children", homeowner=True,
                interests=["Shopping"], device_types=["tv"], propensity_x100=100) for i in range(120)])
            db.add_all([Channel(name=f"C{i}", category=ChannelCategory.entertainment, reach_households=10_000_000,
                                base_cpm_micros=20_000_000) for i in range(6)])
            await db.execute(update(Account).values(balance_micros=10_000_000_000))
            await db.execute(update(Campaign).where(Campaign.id == long_c).values(
                status=CampaignStatus.learning, attribution_window_hours=720))
            await db.execute(update(Campaign).where(Campaign.id == short_c).values(
                status=CampaignStatus.learning, attribution_window_hours=24))
            await db.execute(update(Strategy).values(status=StrategyStatus.active, budget_micros=200_000_000))
            await db.commit()

            await simulate_all(db, 24 * 14, rng=random.Random(11))
            await db.execute(delete(Conversion))  # simulate_all already attributed; start from none
            await db.commit()

            imp = (await db.execute(select(Impression).where(Impression.campaign_id == short_c)
                                    .order_by(Impression.ts).limit(1))).scalar_one()
            other_hh = (await db.execute(select(Household.id).limit(1))).scalar_one()

            def ev(kind, ts, household):
                return Event(ts=ts, account_id=imp.account_id, advertiser_id=imp.advertiser_id,
                             source=EventSource.pixel, event=kind, household_id=household, revenue_micros=0, raw={})

            db.add_all([
                ev("purchase", imp.ts + dt.timedelta(hours=30), imp.household_id),   # past the 24 h campaign window
                ev("purchase", imp.ts - dt.timedelta(days=40), other_hh),            # before any impression
                ev("add_to_cart", imp.ts + dt.timedelta(hours=1), imp.household_id),  # unmapped event type
                ev("page_view", imp.ts + dt.timedelta(hours=1), None),                 # no household
            ])
            await db.commit()
    asyncio.run(go())


async def _conversions(db):
    rows = (await db.execute(select(Conversion.event_id, Conversion.impression_id, Conversion.campaign_id,
                                    Conversion.event, Conversion.lag_seconds, Conversion.revenue_micros))).all()
    return sorted((r[0], r[1], str(r[2]), r[3], r[4], r[5]) for r in rows)


def test_sql_attribution_matches_reference(client):
    _setup(client)

    async def go():
        async with TestSessionLocal() as db:
            n_ref = await _reference_attribution(db)
            ref = await _conversions(db)
            await db.execute(delete(Conversion))
            await db.commit()
            n_sql = await attribution.run_attribution(db)
            got = await _conversions(db)
            again = await attribution.run_attribution(db)  # nothing left to attribute
            total = (await db.execute(select(func.count()).select_from(Conversion))).scalar_one()
            return n_ref, ref, n_sql, got, again, total

    n_ref, ref, n_sql, got, again, total = asyncio.run(go())
    assert n_ref > 20, "the dataset should exercise attribution"
    assert n_sql == n_ref
    assert got == ref
    assert again == 0 and total == n_sql


def test_sql_rollups_match_reference(client):
    _setup(client)
    cols = (StatsDaily.date, StatsDaily.advertiser_id, StatsDaily.campaign_id, StatsDaily.strategy_id,
            StatsDaily.creative_id, StatsDaily.channel_id, StatsDaily.state)
    q = select(*cols, func.sum(StatsDaily.impressions), func.sum(StatsDaily.spend_micros),
               func.sum(StatsDaily.households_reached), func.sum(StatsDaily.sessions), func.sum(StatsDaily.leads),
               func.sum(StatsDaily.purchases), func.sum(StatsDaily.installs),
               func.sum(StatsDaily.revenue_micros)).group_by(*cols)

    async def go():
        async with TestSessionLocal() as db:
            await attribution.run_attribution(db)
            await rollups.rebuild_rollups(db)
            got = sorted(tuple(str(x) for x in r) for r in (await db.execute(q)).all())
            sd = (await db.execute(select(func.sum(StatsDaily.impressions), func.sum(StatsDaily.spend_micros),
                                          func.sum(StatsDaily.sessions + StatsDaily.leads + StatsDaily.purchases
                                                   + StatsDaily.installs)))).one()
            imp_total = (await db.execute(select(func.count()).select_from(Impression))).scalar_one()
            spend_total = (await db.execute(select(func.sum(Impression.cost_micros)))).scalar_one()
            conv_total = (await db.execute(select(func.count()).select_from(Conversion))).scalar_one()
            await _rollups_reference.rebuild_rollups(db)
            ref = sorted(tuple(str(x) for x in r) for r in (await db.execute(q)).all())
            return got, ref, sd, imp_total, spend_total, conv_total

    got, ref, sd, imp_total, spend_total, conv_total = asyncio.run(go())
    assert len(got) > 10
    assert got == ref
    assert int(sd[0]) == imp_total and int(sd[1]) == int(spend_total) and int(sd[2]) == conv_total
