"""M1 acceptance: invite member; API keys returned once."""
from tests.conftest import signup


def test_invite_member(client):
    s = signup(client, "owner@m.io", "Acme")
    h = s["headers"]

    inv = client.post("/api/v1/members/invite", headers=h, json={"email": "teammate@m.io", "role": "admin"})
    assert inv.status_code == 201, inv.text
    body = inv.json()
    assert body["email"] == "teammate@m.io"
    assert body["role"] == "admin"
    assert body["token"]

    members = client.get("/api/v1/members", headers=h).json()
    assert [m["email"] for m in members] == ["owner@m.io"]


def test_cannot_invite_owner(client):
    s = signup(client, "owner2@m.io", "Acme")
    r = client.post("/api/v1/members/invite", headers=s["headers"], json={"email": "x@m.io", "role": "owner"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_ROLE"


def test_api_key_returned_once(client):
    s = signup(client, "owner3@m.io", "Acme")
    h = s["headers"]
    created = client.post("/api/v1/api-keys", headers=h, json={"name": "CI key"})
    assert created.status_code == 201, created.text
    full = created.json()["key"]
    assert full.startswith("lum_")

    # listing never returns the full key again
    listed = client.get("/api/v1/api-keys", headers=h).json()
    assert len(listed) == 1
    assert "key" not in listed[0]


def test_api_key_authenticates(client):
    s = signup(client, "owner4@m.io", "Acme")
    h = s["headers"]
    client.post("/api/v1/advertisers", headers=h, json={"name": "Brand"})
    full = client.post("/api/v1/api-keys", headers=h, json={"name": "k"}).json()["key"]

    # API-key auth (no X-Account-Id needed; account inferred from the key)
    r = client.get("/api/v1/advertisers", headers={"Authorization": f"Bearer {full}"})
    assert r.status_code == 200
    assert [a["name"] for a in r.json()] == ["Brand"]
