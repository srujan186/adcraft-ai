"""P0-6: API keys — scopes are enforced, validated, and last-used is recorded."""
import asyncio

from sqlalchemy import update

from app.models.identity import ApiKey
from tests.conftest import TestSessionLocal, signup


def _key(client, h, **body):
    return client.post("/api/v1/api-keys", headers=h, json={"name": "k", **body})


def _as(key):
    return {"Authorization": f"Bearer {key}"}


def test_read_scope_can_read_but_not_write(client):
    h = signup(client, "ak1@acme.io", "Acme")["headers"]
    key = _key(client, h, scopes=["read"]).json()["key"]
    assert client.get("/api/v1/advertisers", headers=_as(key)).status_code == 200
    r = client.post("/api/v1/advertisers", headers=_as(key), json={"name": "B", "industry": "ecommerce",
                                                                   "timezone": "America/New_York"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "SCOPE_REQUIRED"


def test_write_scope_can_write(client):
    h = signup(client, "ak2@acme.io", "Acme")["headers"]
    key = _key(client, h, scopes=["read", "write"]).json()["key"]
    r = client.post("/api/v1/advertisers", headers=_as(key), json={"name": "B", "industry": "ecommerce",
                                                                   "timezone": "America/New_York"})
    assert r.status_code == 201, r.text


def test_scopes_default_to_read_and_are_validated(client):
    h = signup(client, "ak3@acme.io", "Acme")["headers"]
    assert _key(client, h).json()["scopes"] == ["read"]
    assert _key(client, h, scopes=[]).status_code == 422
    assert _key(client, h, scopes=["admin"]).status_code == 422


def test_last_used_is_recorded_even_for_reads(client):
    h = signup(client, "ak4@acme.io", "Acme")["headers"]
    created = _key(client, h, scopes=["read"]).json()
    assert created["last_used_at"] is None
    client.get("/api/v1/advertisers", headers=_as(created["key"]))
    listed = client.get("/api/v1/api-keys", headers=h).json()
    assert listed[0]["last_used_at"] is not None


def test_revoked_key_is_rejected(client):
    h = signup(client, "ak5@acme.io", "Acme")["headers"]
    created = _key(client, h, scopes=["read"]).json()
    assert client.delete(f"/api/v1/api-keys/{created['id']}", headers=h).status_code == 204
    assert client.get("/api/v1/advertisers", headers=_as(created["key"])).status_code == 401


def test_legacy_keys_without_scopes_keep_full_access(client):
    """Keys created before scopes were enforced stored []; they had full access then."""
    h = signup(client, "ak6@acme.io", "Acme")["headers"]
    created = _key(client, h, scopes=["read"]).json()

    async def make_legacy():
        async with TestSessionLocal() as s:
            await s.execute(update(ApiKey).where(ApiKey.id == created["id"]).values(scopes=[]))
            await s.commit()
    asyncio.run(make_legacy())
    r = client.post("/api/v1/advertisers", headers=_as(created["key"]), json={
        "name": "B", "industry": "ecommerce", "timezone": "America/New_York"})
    assert r.status_code == 201, r.text
