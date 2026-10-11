"""M6: custom audience CSV upload → match rate; lookalike; usable in a strategy."""
import asyncio

from app.models.audience import Audience
from app.models.inventory import Household
from app.services.audiences import run_match
from tests.conftest import TestSessionLocal, signup


def _match(aid):
    """Background tasks use the app's dev session; drive the match on the test DB."""
    async def go():
        async with TestSessionLocal() as db:
            aud = await db.get(Audience, aid)
            await run_match(db, aud)
    asyncio.run(go())


def _advertiser(client, h):
    return client.post(
        "/api/v1/advertisers", headers=h,
        json={"name": "Brand", "industry": "ecommerce", "timezone": "America/New_York"},
    ).json()["id"]


def _seed_households(n=300):
    async def go():
        async with TestSessionLocal() as s:
            s.add_all([
                Household(
                    ip_hash=f"h{i}", zip=f"{10000 + i:05d}", dma_code="500", state="CA",
                    city="Los Angeles", county="LA County", congressional_district="CA-01",
                    timezone="America/Los_Angeles", age_bucket="25-34", gender="female",
                    income_bucket="50k-99k", education="bachelors", family="no_children",
                    homeowner=True, interests=["Shopping"], device_types=["tv"], propensity_x100=100,
                )
                for i in range(n)
            ])
            await s.commit()
    asyncio.run(go())


def test_csv_upload_match_rate_and_strategy_use(client):
    _seed_households()
    h = signup(client, "aud@acme.io", "Acme")["headers"]
    adv = _advertiser(client, h)

    csv = "email,zip\n" + "\n".join(f"user{i}@x.io,{10000 + i:05d}" for i in range(1000))
    r = client.post(
        "/api/v1/audiences/upload",
        headers=h,
        data={"advertiser_id": adv, "name": "My List", "source": "contacts_list"},
        files={"file": ("contacts.csv", csv, "text/csv")},
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    assert r.json()["uploaded_records"] == 1000

    _match(aid)
    aud = client.get(f"/api/v1/audiences/{aid}", headers=h).json()
    assert aud["status"] == "ready"
    assert aud["match_rate"] is not None and 0.5 <= aud["match_rate"] <= 0.8
    assert aud["matched_households"] > 0

    # lookalike from the seed audience
    lk = client.post("/api/v1/audiences/lookalike", headers=h, json={
        "advertiser_id": adv, "name": "Lookalike 5%", "seed_audience_id": aid, "size_pct": 5,
    })
    assert lk.status_code == 201
    _match(lk.json()["id"])
    assert client.get(f"/api/v1/audiences/{lk.json()['id']}", headers=h).json()["status"] == "ready"

    # usable in a strategy include/exclude
    c = client.post("/api/v1/campaigns", headers=h, json={"advertiser_id": adv, "goal": "retargeting", "kpi": "cps"}).json()
    sid = c["strategies"][0]["id"]
    upd = client.patch(f"/api/v1/strategies/{sid}", headers=h, json={"include_audience_ids": [aid]})
    assert upd.status_code == 200
    assert aid in [str(x) for x in upd.json()["include_audience_ids"]]


def test_web_audiences_listed(client):
    h = signup(client, "aud2@acme.io", "Acme")["headers"]
    adv = _advertiser(client, h)
    client.post(f"/api/v1/advertisers/{adv}/pixel", headers=h, json={"install_method": "manual"})
    auds = client.get(f"/api/v1/audiences?advertiser_id={adv}", headers=h).json()
    assert {a["name"] for a in auds} == {"Visitors", "Leads", "Purchasers"}
    assert all(a["source"] == "web_traffic" for a in auds)
