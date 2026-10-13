"""P0-3: /estimate with placement_mode=selected crashed, and the crash reached the browser
without CORS headers (so it showed only "Failed to fetch")."""
import asyncio

from app.models.inventory import Channel, ChannelCategory, Household
from tests.conftest import TestSessionLocal, signup

ORIGIN = "http://localhost:3000"


def _seed():
    """40 households; 25 channels: one small, one large, 23 mid-size."""
    async def go():
        async with TestSessionLocal() as s:
            s.add_all([
                Household(ip_hash=f"e{i}", zip=f"Z{i:05d}", dma_code="500", state="CA", city="LA",
                          county="LA", congressional_district="CA-01", timezone="America/Los_Angeles",
                          age_bucket="25-34", gender="female", income_bucket="50k-99k", education="bachelors",
                          family="no_children", homeowner=True, interests=["Shopping"], device_types=["tv"],
                          propensity_x100=100)
                for i in range(40)
            ])
            reach = [1_000_000, 300_000_000] + [20_000_000] * 23
            chans = [Channel(name=f"Channel {i}", category=ChannelCategory.entertainment,
                             reach_households=r, base_cpm_micros=20_000_000 + i * 100_000)
                     for i, r in enumerate(reach)]
            s.add_all(chans)
            await s.commit()
            return [str(c.id) for c in chans]
    return asyncio.run(go())


def _est(client, h, **strategy):
    base = {"budget_type": "daily", "budget_micros": 50_000_000, "device_types": ["tv"],
            "dayparting": {"preset": "any"}, "locations": {"include": [], "exclude": []}}
    return client.post("/api/v1/estimate", headers={**h, "Origin": ORIGIN},
                       json={"goal": "traffic", "strategy": {**base, **strategy}})


def test_estimate_with_selected_channels(client):
    ids = _seed()
    h = signup(client, "chan@acme.io", "Acme")["headers"]
    every = _est(client, h, placement_mode="all")
    assert every.status_code == 200, every.text
    all_hi = every.json()["audience_households"][1]

    for label, sel in [("1 small", ids[:1]), ("1 large", ids[1:2]), ("20 channels", ids[2:22])]:
        r = _est(client, h, placement_mode="selected", channel_ids=sel)
        assert r.status_code == 200, (label, r.status_code, r.text[:300])
        assert r.json()["audience_households"][1] < all_hi, label


def test_unexpected_errors_are_json_with_cors_headers(client, monkeypatch):
    """Any unhandled exception must come back as our JSON envelope *with* CORS headers, so
    the browser can read it instead of reporting a network failure."""
    import app.routers.campaigns as campaigns

    async def boom(*_a, **_k):
        raise RuntimeError("estimator exploded")

    monkeypatch.setattr(campaigns, "run_estimate", boom)
    h = signup(client, "boom@acme.io", "Acme")["headers"]
    r = _est(client, h, placement_mode="all")
    assert r.status_code == 500
    assert r.headers.get("access-control-allow-origin") == ORIGIN
    assert r.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "exploded" not in r.text  # internals are logged, not sent to the client
