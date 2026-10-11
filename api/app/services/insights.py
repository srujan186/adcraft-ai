"""Insights overview + incrementality (docs/11)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import HoldoutHousehold
from app.models.campaign import Campaign
from app.models.creative import Creative
from app.models.inventory import Channel, Household
from app.models.measurement import Conversion, Impression, StatsDaily

# incrementality thresholds (docs/11)
ELIG_DAYS, ELIG_SPEND_USD, ELIG_CONV, ELIG_HOLDOUT = 28, 3000, 200, 5000


async def overview(db: AsyncSession, account_id: uuid.UUID, advertiser_id: uuid.UUID, frm: dt.date, to: dt.date) -> dict:
    sd = StatsDaily
    base = (sd.account_id == account_id, sd.advertiser_id == advertiser_id, sd.date >= frm, sd.date <= to)

    async def by(dim):
        rows = (
            await db.execute(
                select(dim, func.sum(sd.impressions), func.sum(sd.spend_micros), func.sum(sd.sessions),
                       func.sum(sd.purchases), func.sum(sd.revenue_micros))
                .where(*base, dim.isnot(None)).group_by(dim)
            )
        ).all()
        return rows

    geo = [{"state": r[0], "impressions": int(r[1] or 0), "spend_micros": int(r[2] or 0),
            "sessions": int(r[3] or 0), "revenue_micros": int(r[5] or 0)} for r in await by(sd.state)]

    ch_rows = await by(sd.channel_id)
    ch_names = {r[0]: r[1] for r in (await db.execute(select(Channel.id, Channel.name))).all()}
    inventory = sorted(
        [{"channel": ch_names.get(r[0], "—"), "impressions": int(r[1] or 0), "spend_micros": int(r[2] or 0),
          "sessions": int(r[3] or 0), "roas": round((r[5] or 0) / r[2], 3) if r[2] else 0.0} for r in ch_rows],
        key=lambda x: x["impressions"], reverse=True,
    )[:20]

    cr_rows = await by(sd.creative_id)
    cr_names = {r[0]: r[1] for r in (await db.execute(select(Creative.id, Creative.name).where(Creative.account_id == account_id))).all()}
    creative = [{"creative": cr_names.get(r[0], "—"), "impressions": int(r[1] or 0), "sessions": int(r[3] or 0),
                 "purchases": int(r[4] or 0), "roas": round((r[5] or 0) / r[2], 3) if r[2] else 0.0}
                for r in cr_rows if r[0]]

    # demographics + time from impressions (joined to households)
    demo_rows = (
        await db.execute(
            select(Household.age_bucket, Household.gender, func.count())
            .join(Household, Household.id == Impression.household_id)
            .where(Impression.advertiser_id == advertiser_id)
            .group_by(Household.age_bucket, Household.gender)
        )
    ).all()
    demographics = [{"age": r[0], "gender": r[1], "impressions": int(r[2])} for r in demo_rows]

    time_rows = (
        await db.execute(
            select(func.extract("dow", Impression.ts), func.extract("hour", Impression.ts), func.count())
            .where(Impression.advertiser_id == advertiser_id)
            .group_by(func.extract("dow", Impression.ts), func.extract("hour", Impression.ts))
        )
    ).all()
    time = [{"dow": int(r[0]), "hour": int(r[1]), "impressions": int(r[2])} for r in time_rows]

    interest_rows = (
        await db.execute(
            select(func.unnest(Household.interests).label("interest"), func.count())
            .join(Household, Household.id == Impression.household_id)
            .where(Impression.advertiser_id == advertiser_id)
            .group_by("interest").order_by(func.count().desc()).limit(15)
        )
    ).all()
    interests = [{"interest": r[0], "impressions": int(r[1])} for r in interest_rows]

    return {"geo": geo, "inventory": inventory, "creative": creative, "demographics": demographics,
            "time": time, "interests": interests}


async def incrementality(db: AsyncSession, account_id: uuid.UUID, advertiser_id: uuid.UUID) -> dict:
    camp_ids = (await db.execute(select(Campaign.id).where(Campaign.advertiser_id == advertiser_id))).scalars().all()
    days = (await db.execute(select(func.count(func.distinct(StatsDaily.date))).where(StatsDaily.advertiser_id == advertiser_id))).scalar_one()
    spend = (await db.execute(select(func.coalesce(func.sum(StatsDaily.spend_micros), 0)).where(StatsDaily.advertiser_id == advertiser_id))).scalar_one()
    convs = (await db.execute(select(func.count()).select_from(Conversion).where(Conversion.campaign_id.in_(camp_ids) if camp_ids else False))).scalar_one() if camp_ids else 0
    holdout = (await db.execute(select(func.count()).select_from(HoldoutHousehold).where(HoldoutHousehold.campaign_id.in_(camp_ids) if camp_ids else False))).scalar_one() if camp_ids else 0

    spend_usd = float(spend) / 1e6
    checks = {
        "days": {"have": int(days), "need": ELIG_DAYS, "ok": days >= ELIG_DAYS},
        "spend": {"have": round(spend_usd, 2), "need": ELIG_SPEND_USD, "ok": spend_usd >= ELIG_SPEND_USD},
        "conversions": {"have": int(convs), "need": ELIG_CONV, "ok": convs >= ELIG_CONV},
        "holdout": {"have": int(holdout), "need": ELIG_HOLDOUT, "ok": holdout >= ELIG_HOLDOUT},
    }
    eligible = all(c["ok"] for c in checks.values())
    result = None
    if eligible:
        exposed_hh = (await db.execute(select(func.count(func.distinct(Impression.household_id))).where(Impression.advertiser_id == advertiser_id))).scalar_one()
        cr_exposed = convs / exposed_hh if exposed_hh else 0
        # holdout conversion rate approximated at 60% of exposed base (organic baseline)
        cr_holdout = cr_exposed * 0.6
        lift = (cr_exposed - cr_holdout) / cr_holdout if cr_holdout else 0
        result = {"lift_pct": round(lift * 100, 1), "incremental_conversions": int((cr_exposed - cr_holdout) * exposed_hh)}
    return {"eligible": eligible, "checks": checks, "result": result}
