"""M5: pixel setup + web audiences, /e ingest, status, purchase→audience, app postback."""
import asyncio

from sqlalchemy import func, select

from app.models.audience import Audience, AudienceMember
from app.models.inventory import Household
from tests.conftest import TestSessionLocal, signup


def _advertiser(client, h):
    return client.post(
        "/api/v1/advertisers", headers=h,
        json={"name": "Brand", "industry": "ecommerce", "timezone": "America/New_York"},
    ).json()["id"]


def _one_household() -> str:
    async def go():
        async with TestSessionLocal() as s:
            hh = Household(
                ip_hash="h1", zip="90001", dma_code="500", state="CA", city="Los Angeles",
                county="LA County", congressional_district="CA-01", timezone="America/Los_Angeles",
                age_bucket="25-34", gender="female", income_bucket="50k-99k", education="bachelors",
                family="no_children", homeowner=True, interests=["Shopping"], device_types=["tv"],
                propensity_x100=100,
            )
            s.add(hh)
            await s.commit()
            return str(hh.id)
    return asyncio.run(go())


def _count(model, **where) -> int:
    async def go():
        async with TestSessionLocal() as s:
            stmt = select(func.count()).select_from(model)
            for k, v in where.items():
                stmt = stmt.where(getattr(model, k) == v)
            return (await s.execute(stmt)).scalar_one()
    return asyncio.run(go())


def test_pixel_setup_creates_web_audiences_and_snippet(client):
    h = signup(client, "px@acme.io", "Acme")["headers"]
    adv = _advertiser(client, h)
    r = client.post(f"/api/v1/advertisers/{adv}/pixel", headers=h, json={"install_method": "manual"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["public_key"].startswith("px_")
    assert body["public_key"] in body["snippet"]
    assert _count(Audience, advertiser_id=adv) == 3  # Visitors / Leads / Purchasers


def test_ingest_page_view_marks_seen(client):
    h = signup(client, "px2@acme.io", "Acme")["headers"]
    adv = _advertiser(client, h)
    pixel = client.post(f"/api/v1/advertisers/{adv}/pixel", headers=h, json={"install_method": "manual"}).json()

    assert client.post("/e", json={"k": pixel["public_key"], "ev": "page_view", "url": "http://x"}).status_code == 204
    status = client.get(f"/api/v1/pixels/{pixel['id']}/status", headers=h).json()
    assert status["status"] == "active"
    pv = next(e for e in status["events"] if e["event"] == "page_view")
    assert pv["seen"] is True

    summ = client.get(f"/api/v1/advertisers/{adv}/tracking", headers=h).json()
    assert summ["has_pixel"] is True and summ["events_seen"]["page_view"] is True


def test_purchase_populates_purchasers_audience(client):
    h = signup(client, "px3@acme.io", "Acme")["headers"]
    adv = _advertiser(client, h)
    pixel = client.post(f"/api/v1/advertisers/{adv}/pixel", headers=h, json={"install_method": "shopify"}).json()
    hh = _one_household()

    r = client.post("/e", json={"k": pixel["public_key"], "ev": "purchase", "value": 49.9, "order_id": "o1"},
                    headers={"X-Sim-Household": hh})
    assert r.status_code == 204
    assert _count(AudienceMember) >= 1


def test_campaign_links_pixel_and_test_event(client):
    h = signup(client, "px4@acme.io", "Acme")["headers"]
    adv = _advertiser(client, h)
    pixel = client.post(f"/api/v1/advertisers/{adv}/pixel", headers=h, json={"install_method": "manual"}).json()

    # test-event marks page_view seen without the browser
    st = client.post(f"/api/v1/pixels/{pixel['id']}/test-event", headers=h).json()
    assert any(e["event"] == "page_view" and e["seen"] for e in st["events"])

    # a new campaign auto-links to the advertiser's pixel
    c = client.post("/api/v1/campaigns", headers=h, json={"advertiser_id": adv, "goal": "sales", "kpi": "cpp"}).json()
    assert c["pixel_id"] == pixel["id"]


def test_app_postback(client):
    h = signup(client, "px5@acme.io", "Acme")["headers"]
    adv = _advertiser(client, h)
    app = client.post("/api/v1/apps", headers=h, json={"advertiser_id": adv, "platform": "ios", "mmp": "appsflyer"}).json()
    assert app["postback_url"].endswith(f"/mmp/appsflyer/{app['id']}")
    assert client.post(f"/mmp/appsflyer/{app['id']}", json={"event": "install"}).status_code == 204
    apps = client.get("/api/v1/apps", headers=h).json()
    assert apps[0]["status"] == "connected"
