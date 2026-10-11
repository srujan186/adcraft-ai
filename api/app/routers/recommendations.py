"""Recommendations (list/apply/reject/recompute) + strategy forecast (account-scoped)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import Tenant, get_current_account, require_roles
from app.core.errors import AppError
from app.models.campaign import Strategy
from app.models.identity import Role
from app.models.intelligence import Recommendation, RecommendationStatus
from app.services.recommender import (
    apply_recommendation,
    forecast,
    generate_for_account,
    reject_recommendation,
)

router = APIRouter(tags=["recommendations"])
_EDIT = require_roles(Role.owner, Role.admin, Role.member)


class RejectBody(BaseModel):
    reason_code: str
    note: str | None = None


def _out(r: Recommendation) -> dict:
    return {
        "id": str(r.id), "campaign_id": str(r.campaign_id), "strategy_id": str(r.strategy_id) if r.strategy_id else None,
        "type": r.type.value, "title": r.title, "body": r.body, "projected": r.projected,
        "status": r.status.value, "created_at": r.created_at.isoformat(),
    }


async def _scoped(db, tenant, rec_id) -> Recommendation:
    r = await db.get(Recommendation, rec_id)
    if r is None or r.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Recommendation not found", 404)
    return r


@router.get("/recommendations")
async def list_recommendations(
    status: str = Query(default="open"), tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)
):
    stmt = select(Recommendation).where(Recommendation.account_id == tenant.account.id)
    if status:
        stmt = stmt.where(Recommendation.status == RecommendationStatus(status))
    rows = (await db.execute(stmt.order_by(Recommendation.created_at.desc()))).scalars().all()
    return [_out(r) for r in rows]


@router.post("/recommendations/recompute")
async def recompute(tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)):
    n = await generate_for_account(db, tenant.account.id)
    return {"created": n}


@router.post("/recommendations/{rec_id}/apply")
async def apply(rec_id: uuid.UUID, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)):
    r = await _scoped(db, tenant, rec_id)
    await apply_recommendation(db, r)
    return _out(r)


@router.post("/recommendations/{rec_id}/reject")
async def reject(rec_id: uuid.UUID, body: RejectBody, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)):
    r = await _scoped(db, tenant, rec_id)
    await reject_recommendation(db, r, body.reason_code, body.note)
    return _out(r)


@router.get("/strategies/{strategy_id}/forecast")
async def strategy_forecast(strategy_id: uuid.UUID, tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)):
    s = await db.get(Strategy, strategy_id)
    if s is None or s.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Strategy not found", 404)
    fc = await forecast(db, s)
    if fc is None:
        return {"available": False, "reason": "Needs ≥7 days of delivery."}
    return {"available": True, **fc}
