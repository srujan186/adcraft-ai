"""M8: delivery simulator — spend within ±5%, frequency caps respected, ROAS/CPS visible."""
import asyncio
import datetime as dt

from sqlalchemy import func, select

from app.models.inventory import Channel, Household
from app.models.measurement import Conversion, Impression
from app.services.simulator import simulate_all
from tests.conftest import TestSessionLocal, signup


def _seed(n_hh=2000):
    async def go():
        async with TestSessionLocal() as s:
            s.add_all([
                Household(ip_hash=f"h{i}", zip=f"{10000+i:05d}", dma_code="500", state="CA",
                          city="LA", county="LA County", congressional_district="CA-01",
                          timezone="America/Los_Angeles", age_bucket="25-34", gender="female",
                          income_bucket="50k-99k", education="bachelors", family="no_children",
                          homeowner=True, interests=["Shopping"], device_types=["tv"], propensity_x100=100)
                for i in range(n_hh)
            ])
            # a handful of channels so CPM is well-defined
            s.add_all([
                Channel(name=f"Ch{i}", category="entertainment", publisher=None,
                        reach_households=10_000_000, base_cpm_micros=24_000_000, is_premium=False)
                for i in range(5)
            ])
            await s.commit()
    asyncio.run(go())


def _approved_creative(client, h, account_id, adv):
    from app.models.creative import Creative, CreativeSource, ReviewStatus

    async def go():
        async with TestSessionLocal() as s:
            c = Creative(account_id=account_id, advertiser_id=adv, name="Ad", source=CreativeSource.upload,
                         review_status=ReviewStatus.approved, duration_ms=15000, width=1920, height=1080)
            s.add(c)
            await s.commit()
            return str(c.id)
    return asyncio.run(go())


def _simulate(hours):
    async def go():
        async with TestSessionLocal() as db:
            return await simulate_all(db, hours)
    return asyncio.run(go())


def _agg():
    async def go():
        async with TestSessionLocal() as db:
            spend = (await db.execute(select(func.coalesce(func.sum(Impression.cost_micros), 0)))).scalar_one()
            per_hh = select(func.count().label("c")).select_from(Impression).group_by(Impression.household_id).subquery()
            max_per_hh = (await db.execute(select(func.max(per_hh.c.c)))).scalar_one()
            n_conv = (await db.execute(select(func.count()).select_from(Conversion))).scalar_one()
            return int(spend), int(max_per_hh or 0), int(n_conv)
    return asyncio.run(go())


def test_simulate_168h(client):
    _seed()
    s = signup(client, "sim@acme.io", "Acme")
    h = s["headers"]
    adv = client.post("/api/v1/advertisers", headers=h, json={"name": "Shop", "industry": "ecommerce", "timezone": "America/New_York"}).json()["id"]

    # pixel + events so a Sales campaign passes tracking validation
    pixel = client.post(f"/api/v1/advertisers/{adv}/pixel", headers=h, json={"install_method": "manual"}).json()
    client.post("/e", json={"k": pixel["public_key"], "ev": "page_view"})
    client.post("/e", json={"k": pixel["public_key"], "ev": "purchase", "value": 50, "order_id": "o1"})

    camp = client.post("/api/v1/campaigns", headers=h, json={"advertiser_id": adv, "goal": "sales", "kpi": "cpp"}).json()
    cid, sid = camp["id"], camp["strategies"][0]["id"]
    cr = _approved_creative(client, h, s["account_id"], adv)
    client.patch(f"/api/v1/strategies/{sid}", headers=h, json={
        "creative_ids": [cr], "frequency_cap": {"impressions": 3, "per": "day"},
    })

    client.post("/api/v1/billing/topup", headers=h, json={"amount_micros": 1_000_000_000})
    pub = client.post(f"/api/v1/campaigns/{cid}/publish", headers=h)
    assert pub.status_code == 200, pub.text
    assert pub.json()["status"] == "learning"

    result = _simulate(168)
    assert result["impressions"] > 0

    spend, max_per_hh, n_conv = _agg()
    target = 50_000_000 * 168 / 24  # 7 days of $50/day = $350
    assert 0.95 * target <= spend <= 1.05 * target, f"spend {spend} vs target {target}"
    assert max_per_hh <= 21, f"frequency cap violated: {max_per_hh} > 21 (3/day × 7)"
    assert n_conv > 0

    # ROAS / CPS visible via stats table
    frm = (dt.date.today() - dt.timedelta(days=9)).isoformat()
    tbl = client.get(f"/api/v1/stats/table?level=campaign&from={frm}", headers=h).json()
    row = next(r for r in tbl["items"] if r["id"] == cid)
    assert row["impressions"] > 0 and row["spend_micros"] > 0
    assert row["sessions"] > 0
    assert "roas" in row and "cps_micros" in row
