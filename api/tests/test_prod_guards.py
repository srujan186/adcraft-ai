"""P0-4: developer endpoints and API docs must not be reachable in production."""
import pytest

from app.core.config import settings
from tests.conftest import signup

DEV_ONLY = ["/api/v1/dev/households", "/docs", "/openapi.json"]


@pytest.fixture()
def as_env(monkeypatch):
    def _set(env: str):
        monkeypatch.setattr(settings, "env", env)
    return _set


def test_dev_routes_and_docs_hidden_in_production(client, as_env):
    h = signup(client, "prod@acme.io", "Acme")["headers"]
    as_env("production")
    for path in DEV_ONLY:
        assert client.get(path, headers=h).status_code == 404, path


def test_dev_routes_and_docs_available_in_development(client, as_env):
    h = signup(client, "devmode@acme.io", "Acme")["headers"]
    as_env("development")
    for path in DEV_ONLY:
        assert client.get(path, headers=h).status_code == 200, path


def test_env_defaults_to_production(monkeypatch):
    from app.core.config import Settings
    monkeypatch.delenv("ENV", raising=False)
    assert Settings(_env_file=None).is_production  # fail closed when ENV isn't set
