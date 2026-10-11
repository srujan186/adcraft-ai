"""Campaigns + strategies (list) + estimate + validate."""
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
from app.models.campaign import Campaign, CampaignGoal, CampaignStatus, Strategy
from app.models.identity import Role
from app.models.tracking import Pixel
from app.schemas.campaign import (
    CampaignCreate,
    CampaignDetail,
    CampaignOut,
    CampaignUpdate,
    EstimateRequest,
    EstimateResponse,
    StrategyOut,
    ValidateResponse,
)
from app.services.estimator import estimate as run_estimate
from app.services.publish import pause_campaign, publish_campaign, resume_campaign
from app.services.validation import validate_campaign

router = APIRouter(tags=["campaigns"])

DEFAULT_STRATEGY_NAME = "All Apps & Channels - TV - Entire US"
_EDIT = require_roles(Role.owner, Role.admin, Role.member)


async def _get_campaign(db: AsyncSession, tenant: Tenant, campaign_id: uuid.UUID) -> Campaign:
    c = await db.get(Campaign, campaign_id)
    if c is None or c.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Campaign not found", 404)
    return c


async def _strategies(db: AsyncSession, campaign_id: uuid.UUID) -> list[Strategy]:
    return list(
        (
            await db.execute(
                select(Strategy).where(Strategy.campaign_id == campaign_id).order_by(Strategy.position)
            )
        ).scalars().all()
    )


async def _detail(db: AsyncSession, c: Campaign) -> CampaignDetail:
    strategies = await _strategies(db, c.id)
    return CampaignDetail(
        **CampaignOut.model_validate(c).model_dump(),
        strategies=[StrategyOut.model_validate(s) for s in strategies],
    )


@router.post("/campaigns", response_model=CampaignDetail, status_code=201)
async def create_campaign(
    body: CampaignCreate, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)
) -> CampaignDetail:
    adv = await db.get(Advertiser, body.advertiser_id)
    if adv is None or adv.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Advertiser not found", 404)

    pixel = (
        await db.execute(select(Pixel).where(Pixel.advertiser_id == body.advertiser_id))
    ).scalar_one_or_none()
    c = Campaign(
        account_id=tenant.account.id, advertiser_id=body.advertiser_id, name=body.name,
        goal=body.goal, kpi=body.kpi, status=CampaignStatus.draft,
        pixel_id=pixel.id if pixel else None,
    )
    db.add(c)
    await db.flush()
    db.add(Strategy(campaign_id=c.id, account_id=tenant.account.id, name=DEFAULT_STRATEGY_NAME, position=0))
    await db.commit()
    await db.refresh(c)
    return await _detail(db, c)


@router.get("/campaigns", response_model=list[CampaignOut])
async def list_campaigns(
    status: CampaignStatus | None = None,
    goal: CampaignGoal | None = None,
    advertiser_id: uuid.UUID | None = None,
    tenant: Tenant = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
) -> list[CampaignOut]:
    stmt = select(Campaign).where(
        Campaign.account_id == tenant.account.id, Campaign.status != CampaignStatus.archived
    )
    if status:
        stmt = stmt.where(Campaign.status == status)
    if goal:
        stmt = stmt.where(Campaign.goal == goal)
    if advertiser_id:
        stmt = stmt.where(Campaign.advertiser_id == advertiser_id)
    rows = (await db.execute(stmt.order_by(Campaign.created_at.desc()))).scalars().all()
    return [CampaignOut.model_validate(c) for c in rows]


@router.get("/campaigns/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(
    campaign_id: uuid.UUID, tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)
) -> CampaignDetail:
    return await _detail(db, await _get_campaign(db, tenant, campaign_id))


@router.patch("/campaigns/{campaign_id}", response_model=CampaignDetail)
async def update_campaign(
    campaign_id: uuid.UUID, body: CampaignUpdate, tenant: Tenant = Depends(_EDIT),
    db: AsyncSession = Depends(get_db),
) -> CampaignDetail:
    c = await _get_campaign(db, tenant, campaign_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    await db.commit()
    await db.refresh(c)
    return await _detail(db, c)


@router.delete("/campaigns/{campaign_id}", status_code=204)
async def archive_campaign(
    campaign_id: uuid.UUID, tenant: Tenant = Depends(require_roles(Role.owner, Role.admin)),
    db: AsyncSession = Depends(get_db),
):
    c = await _get_campaign(db, tenant, campaign_id)
    c.status = CampaignStatus.archived
    await db.commit()


@router.post("/campaigns/{campaign_id}/duplicate", response_model=CampaignDetail, status_code=201)
async def duplicate_campaign(
    campaign_id: uuid.UUID, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)
) -> CampaignDetail:
    src = await _get_campaign(db, tenant, campaign_id)
    dup = Campaign(
        account_id=src.account_id, advertiser_id=src.advertiser_id, name=f"{src.name} (copy)",
        goal=src.goal, kpi=src.kpi, kpi_target_micros=src.kpi_target_micros,
        kpi_target_ratio=src.kpi_target_ratio, attribution_window_hours=src.attribution_window_hours,
        status=CampaignStatus.draft,
    )
    db.add(dup)
    await db.flush()
    for s in await _strategies(db, src.id):
        db.add(_copy_strategy(s, dup.id))
    await db.commit()
    await db.refresh(dup)
    return await _detail(db, dup)


@router.get("/campaigns/{campaign_id}/strategies", response_model=list[StrategyOut])
async def list_strategies(
    campaign_id: uuid.UUID, tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)
) -> list[StrategyOut]:
    await _get_campaign(db, tenant, campaign_id)
    return [StrategyOut.model_validate(s) for s in await _strategies(db, campaign_id)]


@router.post("/campaigns/{campaign_id}/strategies", response_model=StrategyOut, status_code=201)
async def add_strategy(
    campaign_id: uuid.UUID, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)
) -> StrategyOut:
    await _get_campaign(db, tenant, campaign_id)
    existing = await _strategies(db, campaign_id)
    s = Strategy(
        campaign_id=campaign_id, account_id=tenant.account.id,
        name=f"Strategy {len(existing) + 1}", position=len(existing),
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return StrategyOut.model_validate(s)


@router.post("/estimate", response_model=EstimateResponse)
async def estimate_endpoint(
    body: EstimateRequest, tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)
) -> EstimateResponse:
    result = await run_estimate(db, body.goal, body.strategy)
    return EstimateResponse(**result)


@router.post("/campaigns/{campaign_id}/validate", response_model=ValidateResponse)
async def validate_endpoint(
    campaign_id: uuid.UUID, tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)
) -> ValidateResponse:
    c = await _get_campaign(db, tenant, campaign_id)
    issues = await validate_campaign(db, c)
    ok = not any(i["level"] == "error" for i in issues)
    return ValidateResponse(ok=ok, issues=issues)


@router.post("/campaigns/{campaign_id}/publish", response_model=CampaignDetail)
async def publish(campaign_id: uuid.UUID, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)):
    c = await _get_campaign(db, tenant, campaign_id)
    await publish_campaign(db, c)
    return await _detail(db, c)


@router.post("/campaigns/{campaign_id}/pause", response_model=CampaignDetail)
async def pause(campaign_id: uuid.UUID, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)):
    c = await _get_campaign(db, tenant, campaign_id)
    await pause_campaign(db, c)
    return await _detail(db, c)


@router.post("/campaigns/{campaign_id}/resume", response_model=CampaignDetail)
async def resume(campaign_id: uuid.UUID, tenant: Tenant = Depends(_EDIT), db: AsyncSession = Depends(get_db)):
    c = await _get_campaign(db, tenant, campaign_id)
    await resume_campaign(db, c)
    return await _detail(db, c)


def _copy_strategy(s: Strategy, campaign_id: uuid.UUID) -> Strategy:
    return Strategy(
        campaign_id=campaign_id, account_id=s.account_id, name=s.name, budget_type=s.budget_type,
        budget_micros=s.budget_micros, start_date=s.start_date, end_date=s.end_date,
        dayparting=s.dayparting, frequency_cap=s.frequency_cap, locations=s.locations,
        interest_segment_ids=list(s.interest_segment_ids or []), suggestions_enabled=s.suggestions_enabled,
        demographics=s.demographics, include_audience_ids=list(s.include_audience_ids or []),
        exclude_audience_ids=list(s.exclude_audience_ids or []), placement_mode=s.placement_mode,
        channel_ids=list(s.channel_ids or []), device_types=list(s.device_types or ["tv"]),
        live_sports_only=s.live_sports_only, bidding_mode=s.bidding_mode, max_cpm_micros=s.max_cpm_micros,
        position=s.position,
    )
