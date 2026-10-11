"""Reporting read endpoints: timeseries + table (campaign/strategy/creative metrics)."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import Tenant, get_current_account
from app.models.campaign import Campaign, Strategy
from app.models.creative import Creative
from app.models.measurement import Impression, StatsDaily

router = APIRouter(prefix="/stats", tags=["stats"])

_METRIC_COL = {
    "impressions": StatsDaily.impressions, "spend": StatsDaily.spend_micros, "sessions": StatsDaily.sessions,
    "leads": StatsDaily.leads, "purchases": StatsDaily.purchases, "installs": StatsDaily.installs,
    "revenue": StatsDaily.revenue_micros, "households": StatsDaily.households_reached,
}


def _range(frm: str | None, to: str | None) -> tuple[dt.date, dt.date]:
    today = dt.date.today()
    t = dt.date.fromisoformat(to) if to else today
    f = dt.date.fromisoformat(frm) if frm else t - dt.timedelta(days=6)
    return f, t


def _derived(m: dict) -> dict:
    spend = m["spend_micros"]
    m["cpm_micros"] = int(spend / m["impressions"] * 1000) if m["impressions"] else 0
    m["cps_micros"] = int(spend / m["sessions"]) if m["sessions"] else 0
    m["cpl_micros"] = int(spend / m["leads"]) if m["leads"] else 0
    m["cpp_micros"] = int(spend / m["purchases"]) if m["purchases"] else 0
    m["cpi_micros"] = int(spend / m["installs"]) if m["installs"] else 0
    m["roas"] = round(m["revenue_micros"] / spend, 3) if spend else 0.0
    return m


@router.get("/timeseries")
async def timeseries(
    metric: str = Query(default="spend"),
    frm: str | None = Query(default=None, alias="from"),
    to: str | None = None,
    campaign_id: uuid.UUID | None = None,
    tenant: Tenant = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    f, t = _range(frm, to)
    col = _METRIC_COL.get(metric, StatsDaily.spend_micros)
    stmt = (
        select(StatsDaily.date, func.sum(col))
        .where(StatsDaily.account_id == tenant.account.id, StatsDaily.date >= f, StatsDaily.date <= t)
        .group_by(StatsDaily.date).order_by(StatsDaily.date)
    )
    if campaign_id:
        stmt = stmt.where(StatsDaily.campaign_id == campaign_id)
    rows = (await db.execute(stmt)).all()
    by_date = {r[0].isoformat(): int(r[1] or 0) for r in rows}
    out = []
    d = f
    while d <= t:
        out.append({"date": d.isoformat(), "value": by_date.get(d.isoformat(), 0)})
        d += dt.timedelta(days=1)
    return {"metric": metric, "points": out}


@router.get("/table")
async def table(
    level: str = Query(default="campaign"),
    frm: str | None = Query(default=None, alias="from"),
    to: str | None = None,
    advertiser_id: uuid.UUID | None = None,
    tenant: Tenant = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    f, t = _range(frm, to)
    key = {"campaign": StatsDaily.campaign_id, "strategy": StatsDaily.strategy_id, "creative": StatsDaily.creative_id}.get(level, StatsDaily.campaign_id)

    base = (
        select(
            key.label("id"),
            func.sum(StatsDaily.impressions).label("impressions"),
            func.sum(StatsDaily.spend_micros).label("spend_micros"),
            func.sum(StatsDaily.sessions).label("sessions"),
            func.sum(StatsDaily.leads).label("leads"),
            func.sum(StatsDaily.purchases).label("purchases"),
            func.sum(StatsDaily.installs).label("installs"),
            func.sum(StatsDaily.revenue_micros).label("revenue_micros"),
        )
        .where(StatsDaily.account_id == tenant.account.id, StatsDaily.date >= f, StatsDaily.date <= t, key.isnot(None))
        .group_by(key)
    )
    if advertiser_id:
        base = base.where(StatsDaily.advertiser_id == advertiser_id)
    rows = (await db.execute(base)).all()

    # distinct households per key (accurate reach), from impressions
    imp_key = {"campaign": Impression.campaign_id, "strategy": Impression.strategy_id, "creative": Impression.creative_id}.get(level, Impression.campaign_id)
    hh_rows = (
        await db.execute(
            select(imp_key, func.count(func.distinct(Impression.household_id)))
            .where(Impression.account_id == tenant.account.id)
            .group_by(imp_key)
        )
    ).all()
    hh = {r[0]: int(r[1]) for r in hh_rows}

    # names
    name_map: dict = {}
    if level == "campaign":
        for c in (await db.execute(select(Campaign.id, Campaign.name).where(Campaign.account_id == tenant.account.id))).all():
            name_map[c[0]] = c[1]
    elif level == "strategy":
        for s in (await db.execute(select(Strategy.id, Strategy.name).where(Strategy.account_id == tenant.account.id))).all():
            name_map[s[0]] = s[1]
    else:
        for c in (await db.execute(select(Creative.id, Creative.name).where(Creative.account_id == tenant.account.id))).all():
            name_map[c[0]] = c[1]

    items = []
    for r in rows:
        m = {
            "id": str(r.id), "name": name_map.get(r.id, "—"),
            "impressions": int(r.impressions or 0), "households": hh.get(r.id, 0),
            "spend_micros": int(r.spend_micros or 0), "sessions": int(r.sessions or 0),
            "leads": int(r.leads or 0), "purchases": int(r.purchases or 0),
            "installs": int(r.installs or 0), "revenue_micros": int(r.revenue_micros or 0),
        }
        items.append(_derived(m))
    return {"level": level, "items": items}
