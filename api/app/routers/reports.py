"""Report builder + saved reports + CSV + Insights (account-scoped)."""
from __future__ import annotations

import csv
import datetime as dt
import io
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import Tenant, get_current_account, require_roles
from app.core.errors import AppError
from app.models.identity import Role
from app.models.reporting import ReportDefinition
from app.services.insights import incrementality, overview
from app.services.reports import run_report

router = APIRouter(tags=["reports"])
_EDIT = require_roles(Role.owner, Role.admin, Role.member)


class RunRequest(BaseModel):
    dimensions: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    date_range: dict[str, Any] = Field(default_factory=dict)


class SaveRequest(RunRequest):
    name: str = Field(min_length=1, max_length=200)
    schedule: dict | None = None
    recipients: list[str] = Field(default_factory=list)


def _default_range(dr: dict) -> dict:
    if not dr.get("from") and not dr.get("to"):
        today = dt.date.today()
        return {"from": (today - dt.timedelta(days=6)).isoformat(), "to": today.isoformat()}
    return dr


@router.post("/reports/run")
async def reports_run(body: RunRequest, tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)):
    return await run_report(db, tenant.account.id, body.dimensions, body.metrics, body.filters, _default_range(body.date_range))


@router.get("/reports")
async def list_reports(tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(ReportDefinition).where(ReportDefinition.account_id == tenant.account.id))).scalars().all()
    return [{"id": str(r.id), "name": r.name, "dimensions": r.dimensions, "metrics": r.metrics,
             "filters": r.filters, "date_range": r.date_range, "schedule": r.schedule} for r in rows]


@router.post("/reports", status_code=201)
async def save_report(body: SaveRequest, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)):
    r = ReportDefinition(
        account_id=tenant.account.id, name=body.name, dimensions=body.dimensions, metrics=body.metrics,
        filters=body.filters, date_range=body.date_range, schedule=body.schedule, recipients=body.recipients,
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return {"id": str(r.id), "name": r.name}


@router.delete("/reports/{report_id}", status_code=204)
async def delete_report(report_id: uuid.UUID, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)):
    r = await db.get(ReportDefinition, report_id)
    if r is None or r.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Report not found", 404)
    await db.delete(r)
    await db.commit()


@router.get("/reports/{report_id}/download")
async def download_report(report_id: uuid.UUID, format: str = "csv", tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)):
    r = await db.get(ReportDefinition, report_id)
    if r is None or r.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Report not found", 404)
    result = await run_report(db, tenant.account.id, r.dimensions, r.metrics, r.filters, _default_range(r.date_range))
    cols = result["dimensions"] + result["metrics"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for row in result["rows"]:
        w.writerow({c: row.get(c, "") for c in cols})
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{r.name}.csv"'})


@router.get("/insights/overview")
async def insights_overview(
    advertiser_id: uuid.UUID,
    frm: str | None = Query(default=None, alias="from"),
    to: str | None = None,
    tenant: Tenant = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    today = dt.date.today()
    t = dt.date.fromisoformat(to) if to else today
    f = dt.date.fromisoformat(frm) if frm else t - dt.timedelta(days=29)
    return await overview(db, tenant.account.id, advertiser_id, f, t)


@router.get("/insights/incrementality")
async def insights_incrementality(advertiser_id: uuid.UUID, tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)):
    return await incrementality(db, tenant.account.id, advertiser_id)
