"""P0-1 verify: the demo account shows data on every screen (dashboard trends, campaign metrics,
reports, insights, forecaster, recommendations), campaigns are out of learning, and re-seeding
replaces the account instead of duplicating it."""
import asyncio
import datetime as dt
import random

import pytest
from sqlalchemy import func, select

from app.models.identity import Account, User
from app.models.inventory import Channel, ChannelCategory, Household
from app.models.measurement import Impression
from app.services.demo import seed_demo
from tests.conftest import TestSessionLocal

EMAIL = "demo@adcraft-demo.com"


def _population():
    async def go():
        async with TestSessionLocal() as db:
            rnd = random.Random(9)
            db.add_all([Household(
                ip_hash=f"p{i}", zip=f"Z{i:05d}", dma_code="500", state=rnd.choice(["CA", "NY", "TX", "FL"]),
                city="X", county="X", congressional_district="CA-01", timezone="America/New_York",
                age_bucket=rnd.choice(["25-34", "35-44", "45-54"]), gender=rnd.choice(["female", "male"]),
                income_bucket="50k-99k", education="bachelors", family="no_children", homeowner=True,
                interests=[rnd.choice(["Shopping", "Fitness", "Travel"])], device_types=["tv"],
                propensity_x100=100) for i in range(300)])
            # high CPM keeps 30 days of demo delivery small enough for a test
            db.add_all([Channel(name=f"Channel {i}", category=ChannelCategory.entertainment,
                                reach_households=20_000_000, base_cpm_micros=250_000_000) for i in range(8)])
            await db.commit()
    asyncio.run(go())


def _seed():
    async def go():
        async with TestSessionLocal() as db:
            return await seed_demo(db, email=EMAIL, password="demo-password-1", days=30, make_media=False)
    return asyncio.run(go())


@pytest.fixture()
def demo(client):
    _population()
    summary = _seed()
    r = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": "demo-password-1"})
    assert r.status_code == 200, r.text
    tok = r.json()
    return summary, {"Authorization": f"Bearer {tok['access_token']}", "X-Account-Id": str(tok["account_id"])}


def test_demo_account_has_data_on_every_screen(client, demo):
    summary, h = demo
    assert summary["impressions"] > 0 and summary["campaigns"] == 3

    trend = client.get("/api/v1/stats/timeseries?metric=spend", headers=h).json()
    assert sum(p["value"] for p in trend["points"]) > 0, "dashboard trend"

    campaigns = client.get("/api/v1/campaigns", headers=h).json()
    assert len(campaigns) == 3
    assert {c["status"] for c in campaigns} == {"delivering"}, "out of learning"

    frm = (dt.date.today() - dt.timedelta(days=30)).isoformat()
    table = client.get(f"/api/v1/stats/table?level=campaign&from={frm}", headers=h).json()["items"]
    assert len(table) == 3 and all(r["impressions"] > 0 and r["spend_micros"] > 0 for r in table), "campaign metrics"

    report = client.post("/api/v1/reports/run", headers=h, json={
        "dimensions": ["date", "campaign"], "metrics": ["impressions", "sessions"], "date_range": {"from": frm}}).json()
    assert sum(r["impressions"] for r in report["rows"]) > 0, "reports"

    adv = client.get("/api/v1/advertisers", headers=h).json()[0]
    assert adv["name"] == "Nimbus Goods"
    overview = client.get(f"/api/v1/insights/overview?advertiser_id={adv['id']}", headers=h).json()
    for card in ("geo", "inventory", "demographics", "time", "interests"):
        assert overview[card], f"insights card {card} is empty"

    detail = client.get(f"/api/v1/campaigns/{campaigns[0]['id']}", headers=h).json()
    forecast = client.get(f"/api/v1/strategies/{detail['strategies'][0]['id']}/forecast", headers=h).json()
    assert forecast.get("available"), "forecaster"

    recs = client.get("/api/v1/recommendations?status=open", headers=h).json()
    assert len(recs) >= 1, "recommendations"


def test_reseeding_replaces_the_demo_account(client, demo):
    first_account = demo[0]["account_id"]
    _seed()

    async def go():
        async with TestSessionLocal() as db:
            users = (await db.execute(select(func.count()).select_from(User).where(User.email == EMAIL))).scalar_one()
            old = await db.get(Account, first_account)
            orphans = (await db.execute(select(func.count()).select_from(Impression)
                                        .where(Impression.account_id == first_account))).scalar_one()
            return users, old, orphans
    users, old, orphans = asyncio.run(go())
    assert users == 1 and old is None and orphans == 0
