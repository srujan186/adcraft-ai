"""M11: Ask Agent reference behavior (3 sections + offer), suggested questions, proposals."""
from tests.conftest import signup


def _setup(client, h):
    adv = client.post("/api/v1/advertisers", headers=h, json={"name": "B", "industry": "ecommerce", "timezone": "America/New_York"}).json()["id"]
    client.post(f"/api/v1/advertisers/{adv}/pixel", headers=h, json={"install_method": "manual"})
    visitors = next(a for a in client.get(f"/api/v1/audiences?advertiser_id={adv}", headers=h).json() if a["name"] == "Visitors")["id"]
    camp = client.post("/api/v1/campaigns", headers=h, json={"advertiser_id": adv, "goal": "sales", "kpi": "cpp"}).json()
    sid = camp["strategies"][0]["id"]
    client.patch(f"/api/v1/strategies/{sid}", headers=h, json={"include_audience_ids": [visitors]})
    return camp["id"], sid


def test_reference_behavior(client):
    h = signup(client, "agent@acme.io", "Acme")["headers"]
    cid, sid = _setup(client, h)

    thread = client.post("/api/v1/agent/threads", headers=h, json={"context": {"campaign_id": cid, "section": "audience"}}).json()
    resp = client.post(f"/api/v1/agent/threads/{thread['id']}/messages", headers=h, json={"message": "What audience should I target?"}).json()
    a = resp["answer"]

    # rubric: 3 bold section headers + an offer
    assert a.count("**") >= 6
    assert "Would you like me to" in a
    # the three expected themes
    assert "retargeting" in a.lower()
    assert "prospecting" in a.lower()
    assert "one important note" in a.lower()


def test_suggested_questions_and_config(client):
    h = signup(client, "agent2@acme.io", "Acme")["headers"]
    qs = client.get("/api/v1/agent/suggested-questions?section=audience", headers=h).json()["questions"]
    assert len(qs) == 2 and "What audience should I target?" in qs
    assert client.get("/api/v1/agent/config", headers=h).json()["configured"] is False


def test_proposal_create_and_apply(client):
    h = signup(client, "agent3@acme.io", "Acme")["headers"]
    cid, sid = _setup(client, h)
    thread = client.post("/api/v1/agent/threads", headers=h, json={"context": {"campaign_id": cid}}).json()
    resp = client.post(f"/api/v1/agent/threads/{thread['id']}/messages", headers=h, json={"message": "yes, set up a second prospecting strategy"}).json()
    assert resp["proposal"] is not None

    before = len(client.get(f"/api/v1/campaigns/{cid}/strategies", headers=h).json())
    client.post(f"/api/v1/agent/proposals/{resp['proposal']['id']}/apply", headers=h)
    after = len(client.get(f"/api/v1/campaigns/{cid}/strategies", headers=h).json())
    assert after == before + 1
