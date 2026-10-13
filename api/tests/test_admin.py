"""P0-1: admin tools exist only with ALLOW_SIMULATION=true and only for ADMIN_EMAILS; simulating
history touches only the caller's own account."""
import asyncio

import pytest
from sqlalchemy import func, select, update

from app.core.config import settings
from app.models.campaign import Campaign, CampaignStatus, Strategy, StrategyStatus
from app.models.identity import Account
from app.models.inventory import Channel, ChannelCategory, Household
from app.models.measurement import Impression
from tests.conftest import TestSessionLocal, signup

ADMIN = "boss@acme.io"


@pytest.fixture()
def admin_on(monkeypatch):
    monkeypatch.setattr(settings, "allow_simulation", True)
    monkeypatch.setattr(settings, "admin_emails", f"{ADMIN}, other-admin@acme.io")


def _live_campaign(client, email):
    s = signup(client, email, "Acme")
    h = s["headers"]
    adv = client.post("/api/v1/advertisers", headers=h, json={
        "name": "Nimbus", "industry": "ecommerce", "timezone": "America/New_York"}).json()["id"]
    cid = client.post("/api/v1/campaigns", headers=h, json={
        "advertiser_id": adv, "name": "Live", "goal": "traffic", "kpi": "cps"}).json()["id"]

    async def go():
        async with TestSessionLocal() as db:
            if not (await db.execute(select(func.count()).select_from(Household))).scalar_one():
                db.add_all([Household(
                    ip_hash=f"ad{i}", zip=f"Z{i:05d}", dma_code="500", state="CA", city="X", county="X",
                    congressional_district="CA-01", timezone="America/Los_Angeles", age_bucket="25-34",
                    gender="female", income_bucket="50k-99k", education="bachelors", family="no_children",
                    homeowner=True, interests=["Shopping"], device_types=["tv"], propensity_x100=100)
                    for i in range(100)])
                db.add_all([Channel(name=f"C{i}", category=ChannelCategory.entertainment,
                                    reach_households=10_000_000, base_cpm_micros=100_000_000) for i in range(4)])
            await db.execute(update(Account).where(Account.id == s["account_id"]).values(balance_micros=10_000_000_000))
            await db.execute(update(Campaign).where(Campaign.id == cid).values(status=CampaignStatus.learning))
            await db.execute(update(Strategy).where(Strategy.campaign_id == cid).values(status=StrategyStatus.active))
            await db.commit()
    asyncio.run(go())
    return h, cid


def _impressions(cid):
    async def go():
        async with TestSessionLocal() as db:
            return (await db.execute(select(func.count()).select_from(Impression)
                                     .where(Impression.campaign_id == cid))).scalar_one()
    return asyncio.run(go())


def test_hidden_when_simulation_is_off(client, monkeypatch):
    monkeypatch.setattr(settings, "allow_simulation", False)
    monkeypatch.setattr(settings, "admin_emails", ADMIN)
    h = signup(client, ADMIN, "Acme")["headers"]
    assert client.get("/api/v1/admin/status", headers=h).status_code == 404
    assert client.post("/api/v1/admin/simulate", headers=h, json={"days": 3}).status_code == 404


def test_hidden_from_non_admins(client, admin_on):
    h = signup(client, "staff@acme.io", "Acme")["headers"]
    assert client.get("/api/v1/admin/status", headers=h).status_code == 404
    assert client.post("/api/v1/admin/simulate", headers=h, json={"days": 3}).status_code == 404
    assert client.post("/api/v1/admin/demo-reset", headers=h, json={"password": "longenough1"}).status_code == 404


def test_admin_simulates_only_their_own_account(client, admin_on):
    h, mine = _live_campaign(client, ADMIN)
    _, theirs = _live_campaign(client, "customer@acme.io")
    assert client.get("/api/v1/admin/status", headers=h).json()["simulation"] is True

    r = client.post("/api/v1/admin/simulate", headers=h, json={"days": 3})
    assert r.status_code == 202, r.text
    assert _impressions(mine) > 0
    assert _impressions(theirs) == 0  # another customer's live campaign is untouched


def test_simulate_days_are_bounded(client, admin_on):
    h = signup(client, ADMIN, "Acme")["headers"]
    assert client.post("/api/v1/admin/simulate", headers=h, json={"days": 0}).status_code == 422
    assert client.post("/api/v1/admin/simulate", headers=h, json={"days": 61}).status_code == 422
