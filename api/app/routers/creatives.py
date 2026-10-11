"""Creatives: upload (direct multipart or presigned) + Library CRUD (account-scoped)."""
from __future__ import annotations

import asyncio
import datetime as dt
import os
import tempfile
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.db import get_db
from app.core.deps import Tenant, get_current_account, require_roles
from app.core.errors import AppError
from app.models.advertiser import Advertiser
from app.models.creative import Creative, CreativeSource, ReviewStatus
from app.models.identity import Role
from app.schemas.creative import (
    CreativeCreate,
    CreativeOut,
    CreativeUpdate,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services.creative_processing import process_creative

router = APIRouter(prefix="/creatives", tags=["creatives"])


def _to_out(c: Creative) -> CreativeOut:
    out = CreativeOut(
        id=c.id, advertiser_id=c.advertiser_id, name=c.name, source=c.source,
        review_status=c.review_status, review_notes=c.review_notes, duration_ms=c.duration_ms,
        width=c.width, height=c.height, size_bytes=c.size_bytes, labels=c.labels or [],
        created_at=c.created_at,
    )
    try:
        if c.thumbnail_key:
            out.thumbnail_url = storage.presign_get(c.thumbnail_key)
        if c.transcoded_key:
            out.video_url = storage.presign_get(c.transcoded_key)
        elif c.file_key:
            out.video_url = storage.presign_get(c.file_key)
    except Exception:  # noqa: BLE001 — storage offline shouldn't break the listing
        pass
    return out


async def _assert_advertiser(db: AsyncSession, tenant: Tenant, advertiser_id: uuid.UUID) -> None:
    adv = await db.get(Advertiser, advertiser_id)
    if adv is None or adv.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Advertiser not found", 404)


async def _get_scoped(db: AsyncSession, tenant: Tenant, creative_id: uuid.UUID) -> Creative:
    c = await db.get(Creative, creative_id)
    if c is None or c.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Creative not found", 404)
    return c


@router.post("/upload-url", response_model=UploadUrlResponse)
async def upload_url(
    body: UploadUrlRequest, tenant: Tenant = Depends(get_current_account)
) -> UploadUrlResponse:
    key = f"uploads/{tenant.account.id}/{uuid.uuid4()}.mp4"
    return UploadUrlResponse(upload_url=storage.presign_put(key, body.content_type), file_key=key)


@router.post("", response_model=CreativeOut, status_code=201)
async def create_from_key(
    body: CreativeCreate,
    background: BackgroundTasks,
    tenant: Tenant = Depends(require_roles(Role.owner, Role.admin, Role.member)),
    db: AsyncSession = Depends(get_db),
) -> CreativeOut:
    await _assert_advertiser(db, tenant, body.advertiser_id)
    c = Creative(
        account_id=tenant.account.id, advertiser_id=body.advertiser_id, name=body.name,
        source=CreativeSource.upload, file_key=body.file_key, review_status=ReviewStatus.pending,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    background.add_task(process_creative, str(c.id))
    return _to_out(c)


@router.post("/upload", response_model=CreativeOut, status_code=201)
async def upload_direct(
    background: BackgroundTasks,
    advertiser_id: uuid.UUID = Form(...),
    name: str = Form(...),
    file: UploadFile = File(...),
    tenant: Tenant = Depends(require_roles(Role.owner, Role.admin, Role.member)),
    db: AsyncSession = Depends(get_db),
) -> CreativeOut:
    """Dev-friendly path: upload the file through the API (no browser→MinIO CORS)."""
    await _assert_advertiser(db, tenant, advertiser_id)
    key = f"uploads/{tenant.account.id}/{uuid.uuid4()}.mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        data = await file.read()
        tmp.write(data)
        tmp_path = tmp.name
    size = len(data)
    await asyncio.to_thread(storage.upload_file, tmp_path, key, "video/mp4")
    try:
        os.remove(tmp_path)
    except OSError:
        pass

    c = Creative(
        account_id=tenant.account.id, advertiser_id=advertiser_id, name=name,
        source=CreativeSource.upload, file_key=key, size_bytes=size, review_status=ReviewStatus.pending,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    background.add_task(process_creative, str(c.id))
    return _to_out(c)


@router.get("", response_model=list[CreativeOut])
async def list_creatives(
    advertiser_id: uuid.UUID | None = None,
    label: str | None = None,
    review_status: ReviewStatus | None = None,
    include_archived: bool = Query(default=False),
    tenant: Tenant = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
) -> list[CreativeOut]:
    stmt = select(Creative).where(Creative.account_id == tenant.account.id)
    if advertiser_id:
        stmt = stmt.where(Creative.advertiser_id == advertiser_id)
    if label:
        stmt = stmt.where(Creative.labels.any(label))
    if review_status:
        stmt = stmt.where(Creative.review_status == review_status)
    if not include_archived:
        stmt = stmt.where(Creative.archived_at.is_(None))
    rows = (await db.execute(stmt.order_by(Creative.created_at.desc()))).scalars().all()
    return [_to_out(c) for c in rows]


@router.get("/{creative_id}", response_model=CreativeOut)
async def get_creative(
    creative_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
) -> CreativeOut:
    return _to_out(await _get_scoped(db, tenant, creative_id))


@router.patch("/{creative_id}", response_model=CreativeOut)
async def update_creative(
    creative_id: uuid.UUID,
    body: CreativeUpdate,
    tenant: Tenant = Depends(require_roles(Role.owner, Role.admin, Role.member)),
    db: AsyncSession = Depends(get_db),
) -> CreativeOut:
    c = await _get_scoped(db, tenant, creative_id)
    if body.name is not None:
        c.name = body.name
    if body.labels is not None:
        c.labels = body.labels
    await db.commit()
    await db.refresh(c)
    return _to_out(c)


@router.delete("/{creative_id}", status_code=204)
async def archive_creative(
    creative_id: uuid.UUID,
    tenant: Tenant = Depends(require_roles(Role.owner, Role.admin)),
    db: AsyncSession = Depends(get_db),
):
    c = await _get_scoped(db, tenant, creative_id)
    c.archived_at = dt.datetime.now(dt.timezone.utc)
    await db.commit()
