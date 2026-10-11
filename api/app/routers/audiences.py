"""Audiences: list, create (JSON or CSV upload), lookalike, refresh (account-scoped)."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import Tenant, get_current_account, require_roles
from app.core.errors import AppError
from app.models.advertiser import Advertiser
from app.models.audience import Audience, AudienceSource, AudienceStatus
from app.models.identity import Role
from app.schemas.audience import AudienceCreate, AudienceOut, LookalikeCreate
from app.services.audiences import match_audience

router = APIRouter(prefix="/audiences", tags=["audiences"])
_EDIT = require_roles(Role.owner, Role.admin, Role.member)


async def _advertiser(db, tenant, advertiser_id):
    adv = await db.get(Advertiser, advertiser_id)
    if adv is None or adv.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Advertiser not found", 404)


async def _scoped(db, tenant, audience_id) -> Audience:
    a = await db.get(Audience, audience_id)
    if a is None or a.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Audience not found", 404)
    return a


@router.get("", response_model=list[AudienceOut])
async def list_audiences(
    advertiser_id: uuid.UUID | None = None,
    source: AudienceSource | None = None,
    include_archived: bool = Query(default=False),
    tenant: Tenant = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Audience).where(Audience.account_id == tenant.account.id)
    if advertiser_id:
        stmt = stmt.where(Audience.advertiser_id == advertiser_id)
    if source:
        stmt = stmt.where(Audience.source == source)
    if not include_archived:
        stmt = stmt.where(Audience.archived_at.is_(None))
    rows = (await db.execute(stmt.order_by(Audience.created_at.desc()))).scalars().all()
    return [AudienceOut.model_validate(a) for a in rows]


@router.post("", response_model=AudienceOut, status_code=201)
async def create_audience(
    body: AudienceCreate, background: BackgroundTasks, tenant: Tenant = Depends(_EDIT),
    db: AsyncSession = Depends(get_db),
):
    await _advertiser(db, tenant, body.advertiser_id)
    aud = Audience(
        account_id=tenant.account.id, advertiser_id=body.advertiser_id, name=body.name,
        source=body.source, definition=body.definition, status=AudienceStatus.processing,
    )
    db.add(aud)
    await db.commit()
    await db.refresh(aud)
    background.add_task(match_audience, str(aud.id))
    return AudienceOut.model_validate(aud)


@router.post("/upload", response_model=AudienceOut, status_code=201)
async def upload_audience(
    background: BackgroundTasks,
    advertiser_id: uuid.UUID = Form(...),
    name: str = Form(...),
    source: AudienceSource = Form(AudienceSource.contacts_list),
    file: UploadFile = File(...),
    tenant: Tenant = Depends(_EDIT),
    db: AsyncSession = Depends(get_db),
):
    await _advertiser(db, tenant, advertiser_id)
    content = (await file.read()).decode("utf-8", errors="ignore")
    lines = [ln for ln in content.splitlines() if ln.strip()]
    uploaded = max(0, len(lines) - 1)  # minus header
    aud = Audience(
        account_id=tenant.account.id, advertiser_id=advertiser_id, name=name, source=source,
        definition={"columns": lines[0] if lines else "", "filename": file.filename},
        uploaded_records=uploaded, status=AudienceStatus.processing,
    )
    db.add(aud)
    await db.commit()
    await db.refresh(aud)
    background.add_task(match_audience, str(aud.id))
    return AudienceOut.model_validate(aud)


@router.post("/lookalike", response_model=AudienceOut, status_code=201)
async def create_lookalike(
    body: LookalikeCreate, background: BackgroundTasks, tenant: Tenant = Depends(_EDIT),
    db: AsyncSession = Depends(get_db),
):
    await _advertiser(db, tenant, body.advertiser_id)
    await _scoped(db, tenant, body.seed_audience_id)
    aud = Audience(
        account_id=tenant.account.id, advertiser_id=body.advertiser_id, name=body.name,
        source=AudienceSource.lookalike, status=AudienceStatus.processing,
        definition={"seed_audience_id": str(body.seed_audience_id), "size_pct": body.size_pct},
    )
    db.add(aud)
    await db.commit()
    await db.refresh(aud)
    background.add_task(match_audience, str(aud.id))
    return AudienceOut.model_validate(aud)


@router.get("/{audience_id}", response_model=AudienceOut)
async def get_audience(
    audience_id: uuid.UUID, tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)
):
    return AudienceOut.model_validate(await _scoped(db, tenant, audience_id))


@router.post("/{audience_id}/refresh", response_model=AudienceOut)
async def refresh_audience(
    audience_id: uuid.UUID, background: BackgroundTasks, tenant: Tenant = Depends(_EDIT),
    db: AsyncSession = Depends(get_db),
):
    aud = await _scoped(db, tenant, audience_id)
    aud.status = AudienceStatus.processing
    await db.commit()
    background.add_task(match_audience, str(aud.id))
    return AudienceOut.model_validate(aud)


@router.delete("/{audience_id}", status_code=204)
async def archive_audience(
    audience_id: uuid.UUID, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)
):
    aud = await _scoped(db, tenant, audience_id)
    aud.archived_at = dt.datetime.now(dt.timezone.utc)
    await db.commit()
