"""M1 acceptance: create 2 advertisers; CRUD + archive."""
from tests.conftest import signup


def test_create_list_two_advertisers(client):
    s = signup(client, "adv@acme.io", "Acme")
    h = s["headers"]

    a1 = client.post("/api/v1/advertisers", headers=h, json={"name": "Brand One", "industry": "ecommerce"})
    a2 = client.post("/api/v1/advertisers", headers=h, json={"name": "Brand Two", "industry": "b2b"})
    assert a1.status_code == 201 and a2.status_code == 201, (a1.text, a2.text)

    rows = client.get("/api/v1/advertisers", headers=h).json()
    assert {r["name"] for r in rows} == {"Brand One", "Brand Two"}
    assert {r["industry"] for r in rows} == {"ecommerce", "b2b"}


def test_update_and_archive(client):
    s = signup(client, "adv2@acme.io", "Acme")
    h = s["headers"]
    adv = client.post("/api/v1/advertisers", headers=h, json={"name": "Brand"}).json()

    upd = client.patch(f"/api/v1/advertisers/{adv['id']}", headers=h, json={"website_url": "https://x.io"})
    assert upd.status_code == 200
    assert upd.json()["website_url"] == "https://x.io"

    assert client.delete(f"/api/v1/advertisers/{adv['id']}", headers=h).status_code == 204
    # archived advertiser is hidden by default, visible with include_archived
    assert client.get("/api/v1/advertisers", headers=h).json() == []
    assert len(client.get("/api/v1/advertisers?include_archived=true", headers=h).json()) == 1
