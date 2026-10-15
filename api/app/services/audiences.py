"""Audience matching (docs/02 §Audiences, docs/06 M6).

No real identity graph ships, so contacts/company/firmographic/connector sources use
a deterministic *synthetic* match (a realistic match rate + a random household sample),
which is enough to drive include/exclude targeting and reporting. Web-traffic audiences
are populated live by the pixel; lookalikes expand to size_pct of the national sample.
"""
from __future__ import annotations

import datetime as dt
import random
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.models.audience import Audience, AudienceMember, AudienceSource, AudienceStatus
from app.models.inventory import Household

_SYNTHETIC_SOURCES = {
    AudienceSource.contacts_list, AudienceSource.company_list, AudienceSource.firmographic,
    AudienceSource.klaviyo, AudienceSource.hubspot, AudienceSource.mailchimp, AudienceSource.customerio,
    AudienceSource.mparticle, AudienceSource.tealium, AudienceSource.twilio, AudienceSource.fivetran,
    AudienceSource.api_upload,
}


async def _random_household_ids(db: AsyncSession, n: int) -> list[uuid.UUID]:
    if n <= 0:
        return []
    rows = (await db.execute(select(Household.id).order_by(func.random()).limit(n))).scalars().all()
    return list(rows)


async def match_audience(audience_id: str) -> None:
    """Background entrypoint (uses the app's real session)."""
    async with SessionLocal() as db:
        aud = await db.get(Audience, audience_id)
        if aud is not None:
            await run_match(db, aud)


async def run_match(db: AsyncSession, aud: Audience) -> None:
    """Core matching against the given session (also used directly in tests)."""
    if True:
        aud.status = AudienceStatus.counting
        await db.commit()

        rng = random.Random(str(aud.id))
        await db.execute(delete(AudienceMember).where(AudienceMember.audience_id == aud.id))

        member_ids: list[uuid.UUID] = []
        match_rate: float | None = None

        if aud.source == AudienceSource.web_traffic:
            # populated live by the pixel; just count what's there
            pass
        elif aud.source == AudienceSource.lookalike:
            total = (await db.execute(select(func.count()).select_from(Household))).scalar_one()
            size_pct = float((aud.definition or {}).get("size_pct", 3))
            member_ids = await _random_household_ids(db, int(total * size_pct / 100))
        elif aud.source in _SYNTHETIC_SOURCES:
            uploaded = aud.uploaded_records or 0
            if aud.source in (AudienceSource.company_list, AudienceSource.firmographic):
                match_rate = round(rng.uniform(0.35, 0.6), 4)
            else:
                match_rate = round(rng.uniform(0.55, 0.8), 4)
            member_ids = await _random_household_ids(db, int(uploaded * match_rate))

        for hid in member_ids:
            db.add(AudienceMember(audience_id=aud.id, household_id=hid))

        count = (
            await db.execute(
                select(func.count()).select_from(AudienceMember).where(AudienceMember.audience_id == aud.id)
            )
        ).scalar_one()
        aud.matched_households = count
        if match_rate is not None:
            aud.match_rate = match_rate
        aud.status = AudienceStatus.ready if count > 0 or aud.source == AudienceSource.web_traffic else AudienceStatus.no_data
        aud.last_synced_at = dt.datetime.now(dt.timezone.utc)
        await db.commit()


# Web-traffic audiences: the pixel endpoint adds a household as each event arrives, but
# simulated delivery inserts events in bulk, so membership is also derived from the events
# table. Set-based and idempotent; runs after every delivery pass.
_WEB_MEMBERS = """
    INSERT INTO audience_members (audience_id, household_id)
    SELECT DISTINCT a.id, e.household_id
    FROM audiences a
    JOIN events e ON e.advertiser_id = a.advertiser_id AND e.household_id IS NOT NULL
    WHERE a.source = 'web_traffic' AND a.archived_at IS NULL {scope}
      AND e.event IN (SELECT jsonb_array_elements_text(a.definition -> 'events'))
    ON CONFLICT DO NOTHING
"""
_WEB_COUNTS = """
    UPDATE audiences a
    SET matched_households = (SELECT COUNT(*) FROM audience_members m WHERE m.audience_id = a.id),
        status = 'ready', last_synced_at = now()
    WHERE a.source = 'web_traffic' AND a.archived_at IS NULL {scope}
"""


async def refresh_web_audiences(db: AsyncSession, account_id: uuid.UUID | None = None) -> None:
    from sqlalchemy import text

    scope, params = ("AND a.account_id = :acc", {"acc": account_id}) if account_id else ("", {})
    await db.execute(text(_WEB_MEMBERS.format(scope=scope)), params)
    await db.execute(text(_WEB_COUNTS.format(scope=scope)), params)
    await db.commit()
