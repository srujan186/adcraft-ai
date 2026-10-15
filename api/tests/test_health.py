"""M0 acceptance: the API boots and reports health."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_api_health() -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["product"] == "AdCraft AI"


def test_openapi_served() -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert r.json()["info"]["title"].endswith("API")


def test_health_answers_head() -> None:
    # Uptime monitors (UptimeRobot's HTTP check) send HEAD; a 405 shows the API as down.
    for path in ("/health", "/api/v1/health"):
        assert client.head(path).status_code == 200
