"""Publish flow + status machine + holdout assignment (docs/07 §Status machine)."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.billing import HoldoutHousehold
from app.models.campaign import BudgetType, Campaign, CampaignStatus, Strategy, StrategyStatus
from app.models.inventory import Household
from app.services.validation import validate_campaign

LEARNING_DAYS = 14
RESUME_LEARNING_DAYS = 5
HOLDOUT_PCT = 0.10
HOLDOUT_CAP = 2000


def _total_daily_micros(strategies: list[Strategy]) -> int:
    total = 0
    for s in strategies:
        if s.budget_type == BudgetType.lifetime and s.start_date and s.end_date:
            days = max(1, (s.end_date - s.start_date).days + 1)
            total += s.budget_micros // days
        else:
            total += s.budget_micros
    return total


async def publish_campaign(db: AsyncSession, campaign: Campaign) -> Campaign:
    issues = await validate_campaign(db, campaign)
    errors = [i for i in issues if i["level"] == "error"]
    if errors:
        raise AppError("VALIDATION_FAILED", "Campaign has blocking issues", 400, {"issues": issues})

    strategies = (await db.execute(select(Strategy).where(Strategy.campaign_id == campaign.id))).scalars().all()
    total_daily = _total_daily_micros(list(strategies))
    from app.models.identity import Account

    acct = await db.get(Account, campaign.account_id)
    if acct is None or acct.balance_micros < total_daily or acct.balance_micros <= 0:
        raise AppError("INSUFFICIENT_BALANCE", "Add funds to publish — your balance can't cover a day of budget.", 402)

    now = dt.datetime.now(dt.timezone.utc)
    future = any(s.start_date and s.start_date > now.date() for s in strategies)
    campaign.published_at = now
    campaign.status = CampaignStatus.scheduled if future else CampaignStatus.learning
    campaign.learning_until = None if future else now + dt.timedelta(days=LEARNING_DAYS)
    for s in strategies:
        s.status = StrategyStatus.active

    # holdout control group (~10% of a bounded eligible sample)
    total_hh = (await db.execute(select(func.count()).select_from(Household))).scalar_one()
    n_holdout = int(min(total_hh, HOLDOUT_CAP) * HOLDOUT_PCT)
    if n_holdout > 0:
        ids = (await db.execute(select(Household.id).order_by(func.random()).limit(n_holdout))).scalars().all()
        for hid in ids:
            db.add(HoldoutHousehold(campaign_id=campaign.id, household_id=hid))

    await db.commit()
    await db.refresh(campaign)
    return campaign


async def pause_campaign(db: AsyncSession, campaign: Campaign) -> Campaign:
    campaign.status = CampaignStatus.paused
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def resume_campaign(db: AsyncSession, campaign: Campaign) -> Campaign:
    now = dt.datetime.now(dt.timezone.utc)
    campaign.status = CampaignStatus.learning
    campaign.learning_until = now + dt.timedelta(days=RESUME_LEARNING_DAYS)
    await db.commit()
    await db.refresh(campaign)
    return campaign
