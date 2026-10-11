"""M1 acceptance: strict multi-tenant isolation — no cross-account leakage.

Hits account-scoped list/read endpoints with two accounts and asserts neither
sees the other's rows, and that a valid token cannot act in a non-member account.
"""
from tests.conftest import signup


def test_no_cross_account_leakage(client):
    a = signup(client, "a@a.io", "Account A")
    b = signup(client, "b@b.io", "Account B")

    adv_a = client.post("/api/v1/advertisers", headers=a["headers"], json={"name": "A-only"}).json()
    adv_b = client.post("/api/v1/advertisers", headers=b["headers"], json={"name": "B-only"}).json()

    # Each account lists ONLY its own advertisers.
    a_names = {r["name"] for r in client.get("/api/v1/advertisers", headers=a["headers"]).json()}
    b_names = {r["name"] for r in client.get("/api/v1/advertisers", headers=b["headers"]).json()}
    assert a_names == {"A-only"}
    assert b_names == {"B-only"}

    # A cannot read B's advertiser by id (scoped 404, not 403, to avoid id enumeration).
    assert client.get(f"/api/v1/advertisers/{adv_b['id']}", headers=a["headers"]).status_code == 404
    assert client.get(f"/api/v1/advertisers/{adv_a['id']}", headers=b["headers"]).status_code == 404

    # Members lists are isolated too.
    a_members = client.get("/api/v1/members", headers=a["headers"]).json()
    assert [m["email"] for m in a_members] == ["a@a.io"]


def test_token_cannot_use_foreign_account(client):
    a = signup(client, "a2@a.io", "Account A")
    b = signup(client, "b2@b.io", "Account B")

    # A's token but claiming B's account id → 403 (not a member).
    forged = {"Authorization": a["headers"]["Authorization"], "X-Account-Id": b["account_id"]}
    r = client.get("/api/v1/advertisers", headers=forged)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


def test_missing_account_header(client):
    a = signup(client, "a3@a.io", "Account A")
    r = client.get("/api/v1/advertisers", headers={"Authorization": a["headers"]["Authorization"]})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "ACCOUNT_REQUIRED"
