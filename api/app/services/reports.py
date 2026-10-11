"""Report builder — safe aggregation over stats_daily from a dimension/metric whitelist."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.creative import Creative
from app.models.inventory import Channel
from app.models.measurement import StatsDaily

DIMS = {
    "date": StatsDaily.date,
    "campaign": StatsDaily.campaign_id,
    "strategy": StatsDaily.strategy_id,
    "creative": StatsDaily.creative_id,
    "channel": StatsDaily.channel_id,
    "region": StatsDaily.state,
}
SUM_METRICS = {
    "spend": StatsDaily.spend_micros, "impressions": StatsDaily.impressions,
    "households": StatsDaily.households_reached, "sessions": StatsDaily.sessions,
    "leads": StatsDaily.leads, "purchases": StatsDaily.purchases,
    "installs": StatsDaily.installs, "revenue": StatsDaily.revenue_micros,
}
DERIVED = {"cpm", "cps", "cpl", "cpp", "cpi", "roas", "frequency"}
MAX_DIMS = 5
MAX_ROWS = 1000


def _derive(row: dict) -> None:
    spend, imp, hh = row.get("spend", 0), row.get("impressions", 0), row.get("households", 0)
    if "cpm" in row:
        row["cpm"] = int(spend / imp * 1000) if imp else 0
    if "cps" in row:
        row["cps"] = int(spend / row["sessions"]) if row.get("sessions") else 0
    if "cpl" in row:
        row["cpl"] = int(spend / row["leads"]) if row.get("leads") else 0
    if "cpp" in row:
        row["cpp"] = int(spend / row["purchases"]) if row.get("purchases") else 0
    if "cpi" in row:
        row["cpi"] = int(spend / row["installs"]) if row.get("installs") else 0
    if "roas" in row:
        row["roas"] = round(row.get("revenue", 0) / spend, 3) if spend else 0.0
    if "frequency" in row:
        row["frequency"] = round(imp / hh, 2) if hh else 0.0


async def run_report(
    db: AsyncSession, account_id: uuid.UUID, dimensions: list[str], metrics: list[str],
    filters: dict | None, date_range: dict | None,
) -> dict:
    dims = [d for d in dimensions if d in DIMS][:MAX_DIMS]
    # metrics needed from sums (include deps for derived)
    sum_needed = {m for m in metrics if m in SUM_METRICS}
    for m in metrics:
        if m in DERIVED:
            sum_needed |= {"spend", "impressions", "households", "sessions", "leads", "purchases", "installs", "revenue"}
    sum_cols = [func.sum(SUM_METRICS[m]).label(m) for m in sum_needed]
    dim_cols = [DIMS[d].label(d) for d in dims]

    stmt = select(*dim_cols, *sum_cols).where(StatsDaily.account_id == account_id)

    dr = date_range or {}
    if dr.get("from"):
        stmt = stmt.where(StatsDaily.date >= dt.date.fromisoformat(dr["from"]))
    if dr.get("to"):
        stmt = stmt.where(StatsDaily.date <= dt.date.fromisoformat(dr["to"]))
    f = filters or {}
    if f.get("campaign_id"):
        stmt = stmt.where(StatsDaily.campaign_id == f["campaign_id"])
    if f.get("advertiser_id"):
        stmt = stmt.where(StatsDaily.advertiser_id == f["advertiser_id"])
    if f.get("channel_id"):
        stmt = stmt.where(StatsDaily.channel_id == f["channel_id"])
    if f.get("state"):
        stmt = stmt.where(StatsDaily.state == f["state"])

    if dim_cols:
        stmt = stmt.group_by(*dim_cols).order_by(*dim_cols)
    stmt = stmt.limit(MAX_ROWS)

    result = (await db.execute(stmt)).mappings().all()

    # id→name lookups
    names: dict[str, dict] = {}
    if "campaign" in dims:
        names["campaign"] = {r[0]: r[1] for r in (await db.execute(select(Campaign.id, Campaign.name).where(Campaign.account_id == account_id))).all()}
    if "creative" in dims:
        names["creative"] = {r[0]: r[1] for r in (await db.execute(select(Creative.id, Creative.name).where(Creative.account_id == account_id))).all()}
    if "channel" in dims:
        names["channel"] = {r[0]: r[1] for r in (await db.execute(select(Channel.id, Channel.name))).all()}

    rows = []
    for r in result:
        row: dict = {}
        for d in dims:
            v = r[d]
            if d in names:
                row[d] = names[d].get(v, "—")
            elif d == "date":
                row[d] = v.isoformat() if v else None
            else:
                row[d] = str(v) if v is not None else None
        for m in sum_needed:
            row[m] = int(r[m] or 0)
        for m in metrics:
            if m in DERIVED:
                row[m] = 0
        _derive(row)
        # keep only requested metrics
        rows.append({**{d: row[d] for d in dims}, **{m: row.get(m, 0) for m in metrics}})

    return {"dimensions": dims, "metrics": metrics, "rows": rows, "row_count": len(rows)}
