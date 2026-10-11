"""M12: Studio generates an approved 15s 1080p creative."""
import asyncio

from app.models.creative import ReviewStatus
from app.services.creative_processing import review_decision
from app.services.studio import render_creative
from tests.conftest import signup


def test_studio_renders_approved_1080p():
    r = asyncio.run(render_creative({
        "business_name": "Nimbus Goods", "duration_s": 15, "tone": "energetic", "cta": "Shop now",
    }))
    assert (r["width"], r["height"]) == (1920, 1080)
    assert 14000 <= r["duration_ms"] <= 16000
    assert review_decision(r["duration_ms"], r["width"], r["height"])[0] == ReviewStatus.approved
    assert len(r["script"]["scenes"]) >= 3


def test_studio_job_endpoint(client):
    h = signup(client, "studio@acme.io", "Acme")["headers"]
    adv = client.post("/api/v1/advertisers", headers=h, json={"name": "B", "industry": "ecommerce", "timezone": "America/New_York"}).json()["id"]
    job = client.post("/api/v1/studio/jobs", headers=h, json={"advertiser_id": adv, "business_name": "Nimbus", "duration_s": 15})
    assert job.status_code == 201
    status = client.get(f"/api/v1/studio/jobs/{job.json()['id']}", headers=h)
    assert status.status_code == 200
    assert status.json()["status"] in {"pending", "processing", "done"}
