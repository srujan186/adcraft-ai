"""Advertisers CRUD (account-scoped)."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import Tenant, get_current_account, require_roles
from app.core.errors import AppError
from app.models.advertiser import Advertiser
from app.models.identity import Role
from app.schemas.advertiser import AdvertiserCreate, AdvertiserOut, AdvertiserUpdate

router = APIRouter(prefix="/advertisers", tags=["advertisers"])


async def _get_scoped(db: AsyncSession, tenant: Tenant, advertiser_id: uuid.UUID) -> Advertiser:
    adv = await db.get(Advertiser, advertiser_id)
    if adv is None or adv.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Advertiser not found", 404)
    return adv


@router.get("", response_model=list[AdvertiserOut])
async def list_advertisers(
    include_archived: bool = Query(default=False),
    tenant: Tenant = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
) -> list[AdvertiserOut]:
    stmt = select(Advertiser).where(Advertiser.account_id == tenant.account.id)
    if not include_archived:
        stmt = stmt.where(Advertiser.archived_at.is_(None))
    rows = (await db.execute(stmt.order_by(Advertiser.created_at))).scalars().all()
    return [AdvertiserOut.model_validate(a) for a in rows]


@router.post("", response_model=AdvertiserOut, status_code=201)
async def create_advertiser(
    body: AdvertiserCreate,
    tenant: Tenant = Depends(require_roles(Role.owner, Role.admin, Role.member)),
    db: AsyncSession = Depends(get_db),
) -> AdvertiserOut:
    adv = Advertiser(account_id=tenant.account.id, **body.model_dump())
    db.add(adv)
    await db.commit()
    await db.refresh(adv)
    return AdvertiserOut.model_validate(adv)


@router.get("/{advertiser_id}", response_model=AdvertiserOut)
async def get_advertiser(
    advertiser_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
) -> AdvertiserOut:
    return AdvertiserOut.model_validate(await _get_scoped(db, tenant, advertiser_id))


@router.patch("/{advertiser_id}", response_model=AdvertiserOut)
async def update_advertiser(
    advertiser_id: uuid.UUID,
    body: AdvertiserUpdate,
    tenant: Tenant = Depends(require_roles(Role.owner, Role.admin, Role.member)),
    db: AsyncSession = Depends(get_db),
) -> AdvertiserOut:
    adv = await _get_scoped(db, tenant, advertiser_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(adv, field, value)
    await db.commit()
    await db.refresh(adv)
    return AdvertiserOut.model_validate(adv)


@router.delete("/{advertiser_id}", status_code=204)
async def archive_advertiser(
    advertiser_id: uuid.UUID,
    tenant: Tenant = Depends(require_roles(Role.owner, Role.admin)),
    db: AsyncSession = Depends(get_db),
):
    adv = await _get_scoped(db, tenant, advertiser_id)
    adv.archived_at = dt.datetime.now(dt.timezone.utc)
    await db.commit()
