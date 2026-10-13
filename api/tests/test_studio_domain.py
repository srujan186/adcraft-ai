"""P0-7: Studio only generates ads from the advertiser's own website."""
import pytest

import app.routers.studio as studio_router
from tests.conftest import signup


@pytest.fixture(autouse=True)
def _no_render(monkeypatch):
    async def noop(*_a, **_k):
        return None
    monkeypatch.setattr(studio_router, "run_studio_job", noop)  # these tests are about the gate only


def _adv(client, h, website):
    body = {"name": "Nimbus Goods", "industry": "ecommerce", "timezone": "America/New_York"}
    if website:
        body["website_url"] = website
    return client.post("/api/v1/advertisers", headers=h, json=body).json()["id"]


def _job(client, h, adv, url):
    body = {"advertiser_id": adv, "business_name": "Nimbus Goods", "duration_s": 15}
    if url is not None:
        body["url"] = url
    return client.post("/api/v1/studio/jobs", headers=h, json=body)


@pytest.mark.parametrize("url", [
    "nimbusgoods.example",
    "https://www.nimbusgoods.example/products/shoes",
    "http://shop.nimbusgoods.example",
    "NimbusGoods.Example:443/sale",
])
def test_own_site_is_allowed(client, url):
    h = signup(client, f"own{abs(hash(url))}@acme.io", "Acme")["headers"]
    adv = _adv(client, h, "https://www.nimbusgoods.example/")
    r = _job(client, h, adv, url)
    assert r.status_code == 201, r.text


@pytest.mark.parametrize("url", [
    "otherbrand.example",
    "https://nimbusgoods.example.evil.example",  # look-alike suffix
    "https://evilnimbusgoods.example",           # look-alike prefix
])
def test_other_sites_are_refused(client, url):
    h = signup(client, f"other{abs(hash(url))}@acme.io", "Acme")["headers"]
    adv = _adv(client, h, "https://www.nimbusgoods.example/")
    r = _job(client, h, adv, url)
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "DOMAIN_MISMATCH"
    assert "nimbusgoods.example" in r.json()["error"]["message"]


def test_url_needs_an_advertiser_website(client):
    h = signup(client, "noweb@acme.io", "Acme")["headers"]
    adv = _adv(client, h, None)
    r = _job(client, h, adv, "nimbusgoods.example")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "WEBSITE_REQUIRED"


def test_business_name_only_needs_no_website(client):
    h = signup(client, "nameonly@acme.io", "Acme")["headers"]
    adv = _adv(client, h, None)
    assert _job(client, h, adv, None).status_code == 201
