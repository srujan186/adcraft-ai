"""M9: report builder (Date×Channel×Sessions) matches campaign-list sum; CSV; incrementality."""
import asyncio
import datetime as dt
import uuid

from app.models.measurement import StatsDaily
from tests.conftest import TestSessionLocal, signup


def _seed_stats(account_id):
    camp = uuid.uuid4()
    adv = uuid.uuid4()
    ch1, ch2 = uuid.uuid4(), uuid.uuid4()
    today = dt.date.today()

    async def go():
        async with TestSessionLocal() as s:
            s.add_all([
                StatsDaily(date=today, account_id=account_id, advertiser_id=adv, campaign_id=camp,
                           channel_id=ch1, state="CA", impressions=100, households_reached=80,
                           spend_micros=2_000_000, sessions=10, revenue_micros=5_000_000, purchases=2),
                StatsDaily(date=today - dt.timedelta(days=1), account_id=account_id, advertiser_id=adv,
                           campaign_id=camp, channel_id=ch2, state="NY", impressions=50, households_reached=40,
                           spend_micros=1_000_000, sessions=5, revenue_micros=0, purchases=0),
            ])
            await s.commit()
    asyncio.run(go())
    return str(camp)


def test_report_matches_campaign_sum(client):
    s = signup(client, "rep@acme.io", "Acme")
    h = s["headers"]
    cid = _seed_stats(s["account_id"])
    frm = (dt.date.today() - dt.timedelta(days=6)).isoformat()

    rep = client.post("/api/v1/reports/run", headers=h, json={
        "dimensions": ["date", "channel"], "metrics": ["sessions", "impressions"],
        "date_range": {"from": frm},
    }).json()
    report_sessions = sum(r["sessions"] for r in rep["rows"])

    tbl = client.get(f"/api/v1/stats/table?level=campaign&from={frm}", headers=h).json()
    camp_sessions = next(r["sessions"] for r in tbl["items"] if r["id"] == cid)

    assert report_sessions == camp_sessions == 15


def test_save_and_download_report(client):
    s = signup(client, "rep2@acme.io", "Acme")
    h = s["headers"]
    _seed_stats(s["account_id"])
    rid = client.post("/api/v1/reports", headers=h, json={
        "name": "Daily by channel", "dimensions": ["date", "channel"], "metrics": ["spend", "sessions"],
    }).json()["id"]
    assert len(client.get("/api/v1/reports", headers=h).json()) == 1
    dl = client.get(f"/api/v1/reports/{rid}/download?format=csv", headers=h)
    assert dl.status_code == 200
    assert "date,channel,spend,sessions" in dl.text


def test_incrementality_not_eligible(client):
    s = signup(client, "rep3@acme.io", "Acme")
    h = s["headers"]
    adv = client.post("/api/v1/advertisers", headers=h, json={"name": "B", "industry": "ecommerce", "timezone": "America/New_York"}).json()["id"]
    inc = client.get(f"/api/v1/insights/incrementality?advertiser_id={adv}", headers=h).json()
    assert inc["eligible"] is False
    assert set(inc["checks"].keys()) == {"days", "spend", "conversions", "holdout"}


def test_insights_overview_does_not_crash(client):
    """The demographics/interests queries joined Household to itself (select from Household,
    join Household), which SQLAlchemy can't compile — the endpoint 500'd for every advertiser."""
    h = signup(client, "ins@acme.io", "Acme")["headers"]
    adv = client.post("/api/v1/advertisers", headers=h, json={
        "name": "Nimbus", "industry": "ecommerce", "timezone": "America/New_York"}).json()["id"]
    r = client.get(f"/api/v1/insights/overview?advertiser_id={adv}", headers=h)
    assert r.status_code == 200, r.text
    assert set(r.json()) >= {"geo", "inventory", "creative", "demographics", "time", "interests"}
