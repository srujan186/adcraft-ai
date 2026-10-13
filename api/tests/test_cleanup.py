"""P0-9: the demo environment holds only the seeded demo account (plus accounts we choose to keep).

`cleanup` reports by default and deletes only with apply=True.
"""
import asyncio

from sqlalchemy import func, select

from app.models.advertiser import Advertiser
from app.models.campaign import Campaign
from app.models.identity import Account, User
from app.models.intelligence import Elasticity
from app.models.measurement import StatsDaily
from app.services import cleanup
from tests.conftest import TestSessionLocal, signup

DEMO = "demo@adcraft-demo.com"


def _account(client, email, company, campaign=None):
    s = signup(client, email, company)
    h = s["headers"]
    adv = client.post("/api/v1/advertisers", headers=h, json={
        "name": company, "industry": "ecommerce", "timezone": "America/New_York"}).json()["id"]
    if campaign:
        client.post("/api/v1/campaigns", headers=h, json={
            "advertiser_id": adv, "name": campaign, "goal": "traffic", "kpi": "cps"})
    return s["account_id"], adv


def _run(fn):
    async def go():
        async with TestSessionLocal() as db:
            return await fn(db)
    return asyncio.run(go())


def _count(model):
    return _run(lambda db: _scalar(db, select(func.count()).select_from(model)))


async def _scalar(db, stmt):
    return (await db.execute(stmt)).scalar_one()


def test_dry_run_reports_and_changes_nothing(client):
    _account(client, DEMO, "Demo Co", "Nimbus — Sales")
    _account(client, "tester@simple.co", "simple.co", "Claude audit (test)")

    report = _run(lambda db: cleanup.cleanup(db, keep_emails=set(), apply=False))
    assert report["applied"] is False
    kept = {a["name"] for a in report["keep"]}
    gone = {a["name"] for a in report["delete"]}
    assert kept == {"Demo Co"} and gone == {"simple.co"}
    (row,) = report["delete"]
    assert row["members"] == ["tester@simple.co"]
    assert row["campaigns"] == ["Claude audit (test)"]
    assert _count(Account) == 2 and _count(Campaign) == 2


def test_apply_removes_everything_but_kept_accounts(client):
    demo_id, _ = _account(client, DEMO, "Demo Co", "Nimbus — Sales")
    _account(client, "owner@acme.io", "Owner Co")
    test_id, test_adv = _account(client, "tester@simple.co", "simple.co", "Claude audit (test)")

    async def rows_without_fks(db):
        camp = (await db.execute(select(Campaign).where(Campaign.account_id == test_id))).scalar_one()
        import datetime as dt
        db.add(StatsDaily(date=dt.date.today(), account_id=test_id, advertiser_id=test_adv,
                          campaign_id=camp.id, impressions=5))
        db.add(Elasticity(advertiser_id=test_adv, goal="traffic", alpha=1, beta=0.5, r2=0.9, n_days=10))
        await db.commit()
    _run(rows_without_fks)

    report = _run(lambda db: cleanup.cleanup(db, keep_emails={"owner@acme.io"}, apply=True))
    assert report["applied"] is True
    names = set(_run(lambda db: _all(db, select(Account.name))))
    assert names == {"Demo Co", "Owner Co"}
    emails = set(_run(lambda db: _all(db, select(User.email))))
    assert emails == {DEMO, "owner@acme.io"}
    assert _run(lambda db: _scalar(db, select(func.count()).select_from(StatsDaily)
                                   .where(StatsDaily.account_id == test_id))) == 0
    assert _run(lambda db: _scalar(db, select(func.count()).select_from(Elasticity)
                                   .where(Elasticity.advertiser_id == test_adv))) == 0
    assert _run(lambda db: _scalar(db, select(func.count()).select_from(Advertiser)
                                   .where(Advertiser.account_id == demo_id))) == 1


def test_refuses_when_the_demo_account_is_missing(client):
    _account(client, "tester@simple.co", "simple.co")
    report = _run(lambda db: cleanup.cleanup(db, keep_emails=set(), apply=True))
    assert report["applied"] is False
    assert "seed-demo" in report["error"]
    assert _count(Account) == 1


async def _all(db, stmt):
    return (await db.execute(stmt)).scalars().all()
