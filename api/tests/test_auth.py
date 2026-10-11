"""M1: signup → login → me."""
from tests.conftest import signup


def test_signup_login_me(client):
    s = signup(client, "owner@acme.io", "Acme Inc")

    me = client.get("/api/v1/auth/me", headers=s["headers"])
    assert me.status_code == 200, me.text
    body = me.json()
    assert body["email"] == "owner@acme.io"
    assert body["active_account"]["name"] == "Acme Inc"
    assert len(body["memberships"]) == 1
    assert body["memberships"][0]["role"] == "owner"

    login = client.post(
        "/api/v1/auth/login", json={"email": "owner@acme.io", "password": "password123"}
    )
    assert login.status_code == 200, login.text
    assert login.json()["account_id"] == s["account_id"]


def test_signup_duplicate_email(client):
    signup(client, "dupe@acme.io", "Acme")
    r = client.post(
        "/api/v1/auth/signup",
        json={"email": "dupe@acme.io", "password": "password123", "company": "Acme2"},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "EMAIL_TAKEN"


def test_login_bad_password(client):
    signup(client, "u@acme.io", "Acme")
    r = client.post("/api/v1/auth/login", json={"email": "u@acme.io", "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_validation_envelope(client):
    r = client.post("/api/v1/auth/signup", json={"email": "not-an-email", "password": "x"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
