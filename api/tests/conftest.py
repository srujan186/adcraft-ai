"""Test harness: a dedicated `lumen_test` database, schema via metadata.create_all,
tables truncated before each test. Uses NullPool so connections never cross event loops.
"""
from __future__ import annotations

import asyncio
import os

os.environ.setdefault("ENV", "development")  # before app import: tests exercise dev routes/docs

import asyncpg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401  (register all tables on Base.metadata)
from app.core.db import Base, get_db
from app.main import app

PG = os.getenv("TEST_PG_BASE", "postgresql://lumen:lumen@localhost:5433")
TEST_DB = "lumen_test"
TEST_URL = f"postgresql+asyncpg://lumen:lumen@localhost:5433/{TEST_DB}"

engine = create_async_engine(TEST_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Background tasks (studio render, audience match, creative processing, simulate) bind
# `SessionLocal` at import from app.core.db — the production engine, pointed at the dev
# DB with a connection pool. A pooled asyncpg connection is bound to the event loop that
# opened it, and TestClient uses a fresh loop per request, so reusing one after its loop
# closed raises "Event loop is closed". Re-point every background-task module at the
# NullPool test session so bg work runs against the test DB on the current loop.
import app.services.audiences as _audiences  # noqa: E402
import app.services.creative_processing as _creative_processing  # noqa: E402
import app.services.simulator as _simulator  # noqa: E402
import app.services.studio as _studio  # noqa: E402

for _m in (_audiences, _creative_processing, _simulator, _studio):
    _m.SessionLocal = TestSessionLocal

_TABLES = "users, accounts, memberships, invitations, api_keys, oauth_apps, advertisers, households, channels, interest_segments, geos, companies, company_households, creatives, campaigns, strategies, strategy_creatives, pixels, pixel_event_types, apps, events, audiences, audience_members, transactions, payment_methods, invoices, coupons, coupon_redemptions, holdout_households, impressions, conversions, stats_daily, report_definitions, recommendations, recommendation_suppressions, elasticities, agent_threads, agent_messages, agent_proposals, studio_jobs"


async def _ensure_db_and_schema() -> None:
    sys_conn = await asyncpg.connect(f"{PG}/postgres")
    try:
        exists = await sys_conn.fetchval("SELECT 1 FROM pg_database WHERE datname=$1", TEST_DB)
        if not exists:
            await sys_conn.execute(f'CREATE DATABASE "{TEST_DB}"')
    finally:
        await sys_conn.close()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def _truncate() -> None:
    async with engine.begin() as conn:
        from sqlalchemy import text

        await conn.execute(text(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session", autouse=True)
def _schema():
    asyncio.run(_ensure_db_and_schema())
    yield


async def _get_test_db():
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture()
def client():
    asyncio.run(_truncate())
    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── helpers ────────────────────────────────────────────────────────────────────
def signup(client: TestClient, email: str, company: str, password: str = "password123"):
    r = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "full_name": "Test User", "company": company},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    return {
        "access_token": data["access_token"],
        "account_id": data["account_id"],
        "headers": {
            "Authorization": f"Bearer {data['access_token']}",
            "X-Account-Id": data["account_id"],
        },
    }
