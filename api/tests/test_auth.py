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


def test_refresh_with_body_token_and_no_cookie(client):
    """Cross-site deploys (web on Vercel, API elsewhere): browsers drop the SameSite=Lax
    refresh cookie, so the client posts the token from the login response instead."""
    r = client.post(
        "/api/v1/auth/signup",
        json={"email": "xsite@acme.io", "password": "password123", "full_name": "X", "company": "Acme"},
    )
    assert r.status_code == 201
    rt = r.json()["refresh_token"]
    assert rt

    client.cookies.clear()  # what the browser effectively has cross-site
    assert client.post("/api/v1/auth/refresh").status_code == 401  # no cookie, no body

    r = client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["refresh_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200

    # an access token is not a refresh token
    bad = client.post("/api/v1/auth/refresh", json={"refresh_token": body["access_token"]})
    assert bad.status_code == 401
