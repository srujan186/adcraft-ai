"""M10: increase_budget recommendation + apply; reject 'on purpose' suppresses permanently."""
import asyncio
import datetime as dt

from sqlalchemy import select

from app.models.campaign import Campaign, CampaignStatus, Strategy, StrategyStatus
from app.models.measurement import StatsDaily
from tests.conftest import TestSessionLocal, signup


def _setup(client, h, account_id):
    adv = client.post("/api/v1/advertisers", headers=h, json={"name": "B", "industry": "ecommerce", "timezone": "America/New_York"}).json()["id"]
    camp = client.post("/api/v1/campaigns", headers=h, json={"advertiser_id": adv, "goal": "sales", "kpi": "cpp"}).json()
    cid, sid = camp["id"], camp["strategies"][0]["id"]

    async def go():
        async with TestSessionLocal() as s:
            c = await s.get(Campaign, cid)
            c.status = CampaignStatus.delivering
            st = await s.get(Strategy, sid)
            st.status = StrategyStatus.active
            today = dt.date.today()
            for d in range(30):  # 30 days, spends full $50/day
                s.add(StatsDaily(
                    date=today - dt.timedelta(days=d), account_id=account_id, advertiser_id=adv,
                    campaign_id=cid, strategy_id=sid, channel_id=None, state="CA",
                    impressions=14000, households_reached=5000, spend_micros=50_000_000,
                    sessions=50, purchases=10, revenue_micros=8_000_000,
                ))
            await s.commit()
    asyncio.run(go())
    return cid, sid


def test_increase_budget_then_apply(client):
    s = signup(client, "rec@acme.io", "Acme")
    h = s["headers"]
    cid, sid = _setup(client, h, s["account_id"])

    assert client.post("/api/v1/recommendations/recompute", headers=h).json()["created"] >= 1
    recs = client.get("/api/v1/recommendations", headers=h).json()
    rec = next(r for r in recs if r["type"] == "increase_budget")
    assert rec["projected"]["uplift_pct"] > 0

    client.post(f"/api/v1/recommendations/{rec['id']}/apply", headers=h)
    strat = client.get(f"/api/v1/strategies/{sid}", headers=h).json()
    assert strat["budget_micros"] > 50_000_000  # budget was increased


def test_reject_on_purpose_suppresses_permanently(client):
    s = signup(client, "rec2@acme.io", "Acme")
    h = s["headers"]
    cid, sid = _setup(client, h, s["account_id"])

    client.post("/api/v1/recommendations/recompute", headers=h)
    rec = next(r for r in client.get("/api/v1/recommendations", headers=h).json() if r["type"] == "increase_budget")
    client.post(f"/api/v1/recommendations/{rec['id']}/reject", headers=h, json={"reason_code": "I use manual bidding on purpose"})

    # recompute again — suppressed permanently, no new open increase_budget
    client.post("/api/v1/recommendations/recompute", headers=h)
    open_recs = client.get("/api/v1/recommendations?status=open", headers=h).json()
    assert not any(r["type"] == "increase_budget" for r in open_recs)


def test_forecast(client):
    s = signup(client, "rec3@acme.io", "Acme")
    h = s["headers"]
    cid, sid = _setup(client, h, s["account_id"])
    fc = client.get(f"/api/v1/strategies/{sid}/forecast", headers=h).json()
    assert fc["available"] is True
    assert fc["recommended_budget_micros"] > fc["current_budget_micros"]
    assert len(fc["points"]) == 40
