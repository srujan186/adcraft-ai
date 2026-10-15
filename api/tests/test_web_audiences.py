"""Web audiences fill from site events however they arrive.

Only the live pixel endpoint added households to Visitors/Leads/Purchasers. Simulated delivery
(the demo account, the delivery loop) writes events straight to the table, so the demo showed
0 households in every audience next to a delivering "Retargeting — Site visitors" strategy.
"""
import asyncio
import datetime as dt

from sqlalchemy import func, select, update

from app.models.audience import Audience, AudienceMember
from app.models.campaign import Campaign, CampaignStatus, Strategy, StrategyStatus
from app.models.identity import Account
from app.models.inventory import Channel, ChannelCategory, Household
from app.models.tracking import Event, EventSource
from app.services.audiences import refresh_web_audiences
from app.services.simulator import simulate_all
from tests.conftest import TestSessionLocal, signup


def _households(n=60):
    return [Household(ip_hash=f"w{i}", zip=f"Z{i:05d}", dma_code="500", state="CA", city="X", county="X",
                      congressional_district="CA-01", timezone="America/Los_Angeles", age_bucket="25-34",
                      gender="female", income_bucket="50k-99k", education="bachelors", family="no_children",
                      homeowner=True, interests=["Shopping"], device_types=["tv"], propensity_x100=100)
            for i in range(n)]


def _setup(client, email):
    s = signup(client, email, "Acme")
    h = s["headers"]
    adv = client.post("/api/v1/advertisers", headers=h, json={
        "name": "Nimbus", "industry": "ecommerce", "timezone": "America/New_York"}).json()["id"]
    client.post(f"/api/v1/advertisers/{adv}/pixel", headers=h, json={"install_method": "manual"})
    return s["account_id"], adv, h


def _sizes(adv):
    async def go():
        async with TestSessionLocal() as db:
            rows = (await db.execute(select(Audience).where(Audience.advertiser_id == adv))).scalars().all()
            members = {a.name: (await db.execute(select(func.count()).select_from(AudienceMember)
                                                 .where(AudienceMember.audience_id == a.id))).scalar_one()
                       for a in rows}
            return {a.name: a.matched_households for a in rows}, members, {a.name: a.status.value for a in rows}
    return asyncio.run(go())


def test_events_written_directly_fill_audiences(client):
    account_id, adv, _ = _setup(client, "aud@acme.io")

    async def go():
        async with TestSessionLocal() as db:
            hh = _households(6)
            db.add_all(hh)
            await db.flush()
            now = dt.datetime.now(dt.timezone.utc)
            for i, (house, ev) in enumerate(zip(hh, ["page_view"] * 4 + ["purchase", "lead"])):
                db.add(Event(ts=now, account_id=account_id, advertiser_id=adv, source=EventSource.pixel,
                             event=ev, household_id=house.id, raw={}))
            db.add(Event(ts=now, account_id=account_id, advertiser_id=adv, source=EventSource.pixel,
                         event="page_view", household_id=hh[0].id, raw={}))  # repeat visit: counted once
            db.add(Event(ts=now, account_id=account_id, advertiser_id=adv, source=EventSource.pixel,
                         event="page_view", household_id=None, raw={}))  # unmatched visit: not a household
            await db.commit()
            await refresh_web_audiences(db, account_id)
            await refresh_web_audiences(db, account_id)  # idempotent
    asyncio.run(go())

    sizes, members, statuses = _sizes(adv)
    assert sizes == {"Visitors": 4, "Leads": 1, "Purchasers": 1}
    assert members == sizes
    assert statuses["Visitors"] == "ready"


def test_simulated_delivery_grows_the_demo_audiences(client):
    account_id, adv, h = _setup(client, "sim@acme.io")
    cid = client.post("/api/v1/campaigns", headers=h, json={
        "advertiser_id": adv, "name": "Live", "goal": "traffic", "kpi": "cps"}).json()["id"]

    async def go():
        async with TestSessionLocal() as db:
            db.add_all(_households(200))
            db.add_all([Channel(name=f"C{i}", category=ChannelCategory.entertainment,
                                reach_households=10_000_000, base_cpm_micros=20_000_000) for i in range(3)])
            await db.execute(update(Account).where(Account.id == account_id).values(balance_micros=10 ** 12))
            await db.execute(update(Campaign).where(Campaign.id == cid).values(status=CampaignStatus.delivering))
            await db.execute(update(Strategy).where(Strategy.campaign_id == cid)
                             .values(status=StrategyStatus.active, budget_micros=5_000_000_000))
            await db.commit()
            await simulate_all(db, 72, account_id=account_id)
            visits = (await db.execute(select(func.count(func.distinct(Event.household_id)))
                                       .where(Event.advertiser_id == adv, Event.event == "page_view"))).scalar_one()
            return visits
    visits = asyncio.run(go())

    assert visits > 0
    sizes, _, _ = _sizes(adv)
    assert sizes["Visitors"] == visits
