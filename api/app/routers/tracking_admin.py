"""Account-scoped tracking admin: pixels, apps, tracking summary, dev households."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import Tenant, get_current_account, require_non_production, require_roles
from app.core.errors import AppError
from app.models.advertiser import Advertiser
from app.models.identity import Role
from app.models.inventory import Household
from app.models.tracking import App, Pixel, PixelEventType
from app.schemas.tracking import AppCreate, AppOut, PixelCreate, PixelCreated, PixelOut
from app.services.tracking import create_pixel, ingest_event, pixel_status, snippet

router = APIRouter(tags=["tracking"])
_EDIT = require_roles(Role.owner, Role.admin, Role.member)


async def _advertiser(db, tenant, advertiser_id) -> Advertiser:
    adv = await db.get(Advertiser, advertiser_id)
    if adv is None or adv.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Advertiser not found", 404)
    return adv


async def _pixel(db, tenant, pixel_id) -> Pixel:
    p = await db.get(Pixel, pixel_id)
    if p is None or p.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Pixel not found", 404)
    return p


@router.post("/advertisers/{advertiser_id}/pixel", response_model=PixelCreated, status_code=201)
async def setup_pixel(
    advertiser_id: uuid.UUID, body: PixelCreate, tenant: Tenant = Depends(_EDIT),
    db: AsyncSession = Depends(get_db),
) -> PixelCreated:
    await _advertiser(db, tenant, advertiser_id)
    existing = (
        await db.execute(select(Pixel).where(Pixel.advertiser_id == advertiser_id))
    ).scalar_one_or_none()
    pixel = existing or await create_pixel(db, tenant.account.id, advertiser_id, body.install_method)
    return PixelCreated(**PixelOut.model_validate(pixel).model_dump(), snippet=snippet(pixel.public_key))


@router.get("/pixels", response_model=list[PixelOut])
async def list_pixels(tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Pixel).where(Pixel.account_id == tenant.account.id))).scalars().all()
    return [PixelOut.model_validate(p) for p in rows]


@router.get("/pixels/{pixel_id}/status")
async def get_pixel_status(
    pixel_id: uuid.UUID, tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)
):
    return await pixel_status(db, await _pixel(db, tenant, pixel_id))


@router.post("/pixels/{pixel_id}/test-event")
async def test_event(
    pixel_id: uuid.UUID, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)
):
    pixel = await _pixel(db, tenant, pixel_id)
    hh = (await db.execute(select(Household.id).order_by(func.random()).limit(1))).scalar_one_or_none()
    await ingest_event(db, pixel.public_key, {"ev": "page_view", "url": "test://event"},
                       str(hh) if hh else None, "127.0.0.1", "test-agent")
    return await pixel_status(db, await _pixel(db, tenant, pixel_id))


@router.get("/advertisers/{advertiser_id}/tracking")
async def tracking_summary(
    advertiser_id: uuid.UUID, tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)
):
    await _advertiser(db, tenant, advertiser_id)
    pixel = (await db.execute(select(Pixel).where(Pixel.advertiser_id == advertiser_id))).scalar_one_or_none()
    app = (await db.execute(select(App).where(App.advertiser_id == advertiser_id))).scalar_one_or_none()
    seen: dict[str, bool] = {}
    if pixel:
        week_ago = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)
        types = (
            await db.execute(select(PixelEventType).where(PixelEventType.pixel_id == pixel.id))
        ).scalars().all()
        for t in types:
            seen[t.event.value] = bool(t.last_seen_at and t.last_seen_at >= week_ago)
    return {
        "has_pixel": pixel is not None,
        "pixel_id": str(pixel.id) if pixel else None,
        "events_seen": seen,
        "has_app": app is not None and app.status.value == "connected",
    }


@router.get("/apps", response_model=list[AppOut])
async def list_apps(tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(App).where(App.account_id == tenant.account.id))).scalars().all()
    out = []
    for a in rows:
        o = AppOut.model_validate(a)
        o.postback_url = f"{settings.public_api_url}/mmp/{a.mmp.value}/{a.id}"
        out.append(o)
    return out


@router.post("/apps", response_model=AppOut, status_code=201)
async def create_app(body: AppCreate, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)):
    await _advertiser(db, tenant, body.advertiser_id)
    a = App(account_id=tenant.account.id, **body.model_dump())
    db.add(a)
    await db.commit()
    await db.refresh(a)
    o = AppOut.model_validate(a)
    o.postback_url = f"{settings.public_api_url}/mmp/{a.mmp.value}/{a.id}"
    return o


@router.get("/dev/households", dependencies=[Depends(require_non_production)])
async def dev_households(tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Household).order_by(func.random()).limit(8))).scalars().all()
    return [
        {"id": str(h.id), "city": h.city, "state": h.state, "age_bucket": h.age_bucket,
         "gender": h.gender, "interests": (h.interests or [])[:3]}
        for h in rows
    ]
