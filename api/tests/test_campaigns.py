"""M4: campaign create (default strategy), strategies, validate, estimate filtering."""
import asyncio
import uuid

from app.models.inventory import Household, InterestSegment
from tests.conftest import TestSessionLocal, signup


def _advertiser(client, h):
    return client.post(
        "/api/v1/advertisers", headers=h,
        json={"name": "Brand", "industry": "ecommerce", "timezone": "America/New_York"},
    ).json()["id"]


def test_create_campaign_has_default_strategy(client):
    h = signup(client, "camp@acme.io", "Acme")["headers"]
    adv = _advertiser(client, h)
    r = client.post(
        "/api/v1/campaigns", headers=h,
        json={"advertiser_id": adv, "name": "My Campaign", "goal": "traffic", "kpi": "cps"},
    )
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["status"] == "draft"
    assert len(c["strategies"]) == 1
    assert c["strategies"][0]["name"] == "All Apps & Channels - TV - Entire US"
    assert client.get("/api/v1/campaigns", headers=h).json()[0]["id"] == c["id"]


def test_add_update_duplicate_strategy(client):
    h = signup(client, "camp2@acme.io", "Acme")["headers"]
    adv = _advertiser(client, h)
    c = client.post("/api/v1/campaigns", headers=h, json={"advertiser_id": adv, "goal": "awareness", "kpi": "cpm"}).json()
    cid = c["id"]
    s2 = client.post(f"/api/v1/campaigns/{cid}/strategies", headers=h)
    assert s2.status_code == 201
    assert len(client.get(f"/api/v1/campaigns/{cid}/strategies", headers=h).json()) == 2
    sid = s2.json()["id"]
    upd = client.patch(f"/api/v1/strategies/{sid}", headers=h, json={"budget_micros": 100_000_000})
    assert upd.status_code == 200 and upd.json()["budget_micros"] == 100_000_000


def test_validate_reports_missing_tracking_and_creative(client):
    h = signup(client, "camp3@acme.io", "Acme")["headers"]
    adv = _advertiser(client, h)
    cid = client.post("/api/v1/campaigns", headers=h, json={"advertiser_id": adv, "goal": "traffic", "kpi": "cps"}).json()["id"]
    v = client.post(f"/api/v1/campaigns/{cid}/validate", headers=h).json()
    codes = {i["code"] for i in v["issues"]}
    assert v["ok"] is False
    assert "MISSING_TRACKING" in codes
    assert "NO_CREATIVE" in codes


def _seed_households():
    async def go():
        async with TestSessionLocal() as s:
            seg = InterestSegment(name="TestInt", reach_households=5_000_000)
            s.add(seg)
            await s.flush()
            rows = []
            for i in range(60):
                narrow = i < 15
                rows.append(Household(
                    ip_hash=f"h{i}", zip="ZEST01" if narrow else f"Z{i:05d}", dma_code="500",
                    state="CA", city="Los Angeles", county="LA County", congressional_district="CA-01",
                    timezone="America/Los_Angeles", age_bucket="25-34", gender="female",
                    income_bucket="50k-99k", education="bachelors", family="no_children", homeowner=True,
                    interests=["TestInt"] if narrow else ["Shopping"], device_types=["tv"], propensity_x100=100,
                ))
            s.add_all(rows)
            await s.commit()
            return str(seg.id)
    return asyncio.run(go())


def test_estimate_filters_narrow_vs_broad(client):
    seg_id = _seed_households()
    h = signup(client, "camp4@acme.io", "Acme")["headers"]
    base = {"budget_type": "daily", "budget_micros": 50_000_000, "placement_mode": "all",
            "device_types": ["tv"], "dayparting": {"preset": "any"}}

    broad = client.post("/api/v1/estimate", headers=h, json={
        "goal": "traffic", "strategy": {**base, "locations": {"include": [], "exclude": []}},
    }).json()
    narrow = client.post("/api/v1/estimate", headers=h, json={
        "goal": "traffic", "strategy": {
            **base, "locations": {"include": [{"type": "zip", "code": "ZEST01"}], "exclude": []},
            "interest_segment_ids": [seg_id],
        },
    }).json()

    assert broad["deliverability"] in {"insufficient", "limited", "good", "excellent"}
    assert broad["audience_households"][1] > narrow["audience_households"][1]
