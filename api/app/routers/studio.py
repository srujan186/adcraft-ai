"""AI Studio jobs: create (URL → creative) + poll (account-scoped)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.db import get_db
from app.core.deps import Tenant, get_current_account, require_roles
from app.core.errors import AppError
from app.models.advertiser import Advertiser
from app.models.creative import Creative
from app.models.identity import Role
from app.models.studio import StudioJob
from app.services.studio import run_studio_job

router = APIRouter(prefix="/studio", tags=["studio"])
_EDIT = require_roles(Role.owner, Role.admin, Role.member)


class StudioJobCreate(BaseModel):
    advertiser_id: uuid.UUID
    url: str | None = None
    business_name: str | None = None
    duration_s: int = Field(default=15)
    voice: str = "female_warm"
    tone: str = "informative"
    cta: str | None = None


@router.post("/jobs", status_code=201)
async def create_job(body: StudioJobCreate, background: BackgroundTasks, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)):
    adv = await db.get(Advertiser, body.advertiser_id)
    if adv is None or adv.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Advertiser not found", 404)
    job = StudioJob(
        account_id=tenant.account.id, advertiser_id=body.advertiser_id,
        input={"url": body.url, "business_name": body.business_name or adv.name,
               "duration_s": body.duration_s, "voice": body.voice, "tone": body.tone, "cta": body.cta},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    background.add_task(run_studio_job, str(job.id))
    return {"id": str(job.id), "status": job.status.value}


@router.get("/jobs/{job_id}")
async def get_job(job_id: uuid.UUID, tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)):
    job = await db.get(StudioJob, job_id)
    if job is None or job.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Job not found", 404)
    out = {"id": str(job.id), "status": job.status.value, "error": job.error, "creative": None}
    if job.output_creative_id:
        c = await db.get(Creative, job.output_creative_id)
        if c:
            out["creative"] = {
                "id": str(c.id), "name": c.name, "review_status": c.review_status.value,
                "duration_ms": c.duration_ms, "width": c.width, "height": c.height,
                "thumbnail_url": storage.presign_get(c.thumbnail_key) if c.thumbnail_key else None,
                "video_url": storage.presign_get(c.transcoded_key) if c.transcoded_key else None,
            }
    return out
