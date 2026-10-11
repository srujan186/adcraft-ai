"""M7: top-up, publish gating on balance, status machine, holdout, coupon."""
import asyncio

from sqlalchemy import func, select

from app.models.billing import Coupon, HoldoutHousehold
from app.models.creative import Creative, CreativeSource, ReviewStatus
from app.models.inventory import Household
from tests.conftest import TestSessionLocal, signup


def _advertiser(client, h):
    return client.post(
        "/api/v1/advertisers", headers=h,
        json={"name": "Brand", "industry": "ecommerce", "timezone": "America/New_York"},
    ).json()["id"]


def _seed_households(n=50):
    async def go():
        async with TestSessionLocal() as s:
            s.add_all([
                Household(ip_hash=f"h{i}", zip=f"{10000+i:05d}", dma_code="500", state="CA",
                          city="LA", county="LA County", congressional_district="CA-01",
                          timezone="America/Los_Angeles", age_bucket="25-34", gender="female",
                          income_bucket="50k-99k", education="bachelors", family="no_children",
                          homeowner=True, interests=["Shopping"], device_types=["tv"], propensity_x100=100)
                for i in range(n)
            ])
            await s.commit()
    asyncio.run(go())


def _approved_creative(account_id, advertiser_id):
    async def go():
        async with TestSessionLocal() as s:
            c = Creative(account_id=account_id, advertiser_id=advertiser_id, name="Ad",
                         source=CreativeSource.upload, review_status=ReviewStatus.approved,
                         duration_ms=15000, width=1920, height=1080)
            s.add(c)
            await s.commit()
            return str(c.id)
    return asyncio.run(go())


def _make_coupon(code, amount_micros):
    async def go():
        async with TestSessionLocal() as s:
            s.add(Coupon(code=code, amount_micros=amount_micros, max_redemptions=5))
            await s.commit()
    asyncio.run(go())


def _count(model, **where):
    async def go():
        async with TestSessionLocal() as s:
            stmt = select(func.count()).select_from(model)
            for k, v in where.items():
                stmt = stmt.where(getattr(model, k) == v)
            return (await s.execute(stmt)).scalar_one()
    return asyncio.run(go())


def test_topup_and_balance(client):
    s = signup(client, "bill@acme.io", "Acme")
    h = s["headers"]
    assert client.get("/api/v1/billing/balance", headers=h).json()["balance_micros"] == 0
    txn = client.post("/api/v1/billing/topup", headers=h, json={"amount_micros": 500_000_000}).json()
    assert txn["type"] == "topup" and txn["balance_after_micros"] == 500_000_000
    assert client.get("/api/v1/billing/balance", headers=h).json()["balance_micros"] == 500_000_000


def test_publish_requires_balance_then_learns(client):
    _seed_households()
    s = signup(client, "bill2@acme.io", "Acme")
    h = s["headers"]
    adv = _advertiser(client, h)
    cid_resp = client.post("/api/v1/campaigns", headers=h, json={"advertiser_id": adv, "goal": "awareness", "kpi": "cpm"}).json()
    cid = cid_resp["id"]
    sid = cid_resp["strategies"][0]["id"]
    cr = _approved_creative(s["account_id"], adv)
    client.patch(f"/api/v1/strategies/{sid}", headers=h, json={"creative_ids": [cr]})

    # $0 balance → INSUFFICIENT_BALANCE
    pub = client.post(f"/api/v1/campaigns/{cid}/publish", headers=h)
    assert pub.status_code == 402
    assert pub.json()["error"]["code"] == "INSUFFICIENT_BALANCE"

    client.post("/api/v1/billing/topup", headers=h, json={"amount_micros": 500_000_000})
    pub2 = client.post(f"/api/v1/campaigns/{cid}/publish", headers=h)
    assert pub2.status_code == 200, pub2.text
    assert pub2.json()["status"] == "learning"
    assert _count(HoldoutHousehold, campaign_id=cid) > 0

    # pause / resume status machine
    assert client.post(f"/api/v1/campaigns/{cid}/pause", headers=h).json()["status"] == "paused"
    assert client.post(f"/api/v1/campaigns/{cid}/resume", headers=h).json()["status"] == "learning"


def test_payment_method_and_coupon(client):
    h = signup(client, "bill3@acme.io", "Acme")["headers"]
    pm = client.post("/api/v1/billing/payment-methods", headers=h,
                     json={"number": "4242424242424242", "exp_month": 12, "exp_year": 2030}).json()
    assert pm["brand"] == "Visa" and pm["last4"] == "4242"

    _make_coupon("WELCOME50", 50_000_000)
    txn = client.post("/api/v1/billing/coupons/redeem", headers=h, json={"code": "WELCOME50"}).json()
    assert txn["type"] == "coupon" and txn["amount_micros"] == 50_000_000
    assert client.get("/api/v1/billing/balance", headers=h).json()["balance_micros"] == 50_000_000
