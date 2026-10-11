"""Strategy-level operations: get, update (incl. creatives), delete, duplicate."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import Tenant, get_current_account, require_roles
from app.core.errors import AppError
from app.models.campaign import Strategy, StrategyCreative
from app.models.creative import Creative
from app.models.identity import Role
from app.schemas.campaign import StrategyOut, StrategyUpdate

router = APIRouter(prefix="/strategies", tags=["strategies"])
_EDIT = require_roles(Role.owner, Role.admin, Role.member)


async def _get_scoped(db: AsyncSession, tenant: Tenant, strategy_id: uuid.UUID) -> Strategy:
    s = await db.get(Strategy, strategy_id)
    if s is None or s.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Strategy not found", 404)
    return s


@router.get("/{strategy_id}", response_model=StrategyOut)
async def get_strategy(
    strategy_id: uuid.UUID, tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)
) -> StrategyOut:
    return StrategyOut.model_validate(await _get_scoped(db, tenant, strategy_id))


@router.patch("/{strategy_id}", response_model=StrategyOut)
async def update_strategy(
    strategy_id: uuid.UUID, body: StrategyUpdate, tenant: Tenant = Depends(_EDIT),
    db: AsyncSession = Depends(get_db),
) -> StrategyOut:
    s = await _get_scoped(db, tenant, strategy_id)
    data = body.model_dump(exclude_unset=True)
    creative_ids = data.pop("creative_ids", None)
    for field, value in data.items():
        setattr(s, field, value)

    if creative_ids is not None:
        # verify all creatives belong to the account
        rows = (
            await db.execute(
                select(Creative.id).where(Creative.id.in_(creative_ids), Creative.account_id == tenant.account.id)
            )
        ).scalars().all()
        valid = set(rows)
        await db.execute(delete(StrategyCreative).where(StrategyCreative.strategy_id == s.id))
        for cid in creative_ids:
            if cid in valid:
                db.add(StrategyCreative(strategy_id=s.id, creative_id=cid, weight=1))

    await db.commit()
    await db.refresh(s)
    return StrategyOut.model_validate(s)


@router.delete("/{strategy_id}", status_code=204)
async def delete_strategy(
    strategy_id: uuid.UUID, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)
):
    s = await _get_scoped(db, tenant, strategy_id)
    await db.delete(s)
    await db.commit()


@router.post("/{strategy_id}/duplicate", response_model=StrategyOut, status_code=201)
async def duplicate_strategy(
    strategy_id: uuid.UUID, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)
) -> StrategyOut:
    s = await _get_scoped(db, tenant, strategy_id)
    n = (
        await db.execute(
            select(func.count()).select_from(Strategy).where(Strategy.campaign_id == s.campaign_id)
        )
    ).scalar_one()
    dup = Strategy(
        campaign_id=s.campaign_id, account_id=s.account_id, name=f"{s.name} (copy)",
        budget_type=s.budget_type, budget_micros=s.budget_micros, start_date=s.start_date,
        end_date=s.end_date, dayparting=s.dayparting, frequency_cap=s.frequency_cap,
        locations=s.locations, interest_segment_ids=list(s.interest_segment_ids or []),
        suggestions_enabled=s.suggestions_enabled, demographics=s.demographics,
        include_audience_ids=list(s.include_audience_ids or []),
        exclude_audience_ids=list(s.exclude_audience_ids or []), placement_mode=s.placement_mode,
        channel_ids=list(s.channel_ids or []), device_types=list(s.device_types or ["tv"]),
        live_sports_only=s.live_sports_only, bidding_mode=s.bidding_mode, max_cpm_micros=s.max_cpm_micros,
        position=n,
    )
    db.add(dup)
    await db.commit()
    await db.refresh(dup)
    return StrategyOut.model_validate(dup)
