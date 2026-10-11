"""Campaign publish validation (docs/06 §Validation codes)."""
from __future__ import annotations

import datetime as dt
import statistics

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import BiddingMode, BudgetType, Campaign, CampaignGoal, Strategy, StrategyCreative
from app.models.creative import Creative, ReviewStatus
from app.models.inventory import Channel
from app.models.tracking import App, AppStatus, EventType, Pixel, PixelEventType
from app.services.estimator import estimate

MIN_DAILY_MICROS = 50_000_000  # $50/day

# goal -> web events that must have been seen (last 7d) before publish
REQUIRED_EVENTS = {
    CampaignGoal.traffic: [EventType.page_view],
    CampaignGoal.retargeting: [EventType.page_view],
    CampaignGoal.leads: [EventType.page_view, EventType.lead],
    CampaignGoal.sales: [EventType.page_view, EventType.purchase],
}


async def _tracking_issues(db: AsyncSession, campaign: Campaign) -> list[dict]:
    out: list[dict] = []
    if campaign.goal == CampaignGoal.app_promotion:
        app = (
            await db.execute(select(App).where(App.advertiser_id == campaign.advertiser_id))
        ).scalar_one_or_none()
        if app is None or app.status != AppStatus.connected:
            out.append(_issue("error", "campaign", "MISSING_TRACKING",
                             "App Promotion campaigns require App Tracking through your MMP."))
        return out

    required = REQUIRED_EVENTS.get(campaign.goal)
    if not required:
        return out
    pixel = (
        await db.execute(select(Pixel).where(Pixel.advertiser_id == campaign.advertiser_id))
    ).scalar_one_or_none()
    if pixel is None:
        out.append(_issue("error", "campaign", "MISSING_TRACKING",
                         "This goal requires a pixel on the advertiser's site."))
        return out
    week_ago = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)
    types = (
        await db.execute(select(PixelEventType).where(PixelEventType.pixel_id == pixel.id))
    ).scalars().all()
    seen = {t.event for t in types if t.last_seen_at and t.last_seen_at >= week_ago}
    missing = [e.value.replace("_", " ").title() for e in required if e not in seen]
    if missing:
        out.append(_issue("error", "campaign", "MISSING_TRACKING",
                         f"{' and '.join(missing)} events not set up yet — this goal needs them on your site."))
    return out


def _issue(level, step, code, message, field=None) -> dict:
    return {"level": level, "step": step, "field": field, "code": code, "message": message}


async def validate_campaign(db: AsyncSession, campaign: Campaign) -> list[dict]:
    issues: list[dict] = []

    # Step 1 — tracking requirements (event-based)
    issues.extend(await _tracking_issues(db, campaign))

    strategies = (
        await db.execute(select(Strategy).where(Strategy.campaign_id == campaign.id))
    ).scalars().all()
    if not strategies:
        issues.append(_issue("error", "strategy", "NO_STRATEGY", "Add at least one strategy."))
        return issues

    # median channel CPM floor (for manual-bid check)
    floors = (await db.execute(select(Channel.base_cpm_micros))).scalars().all()
    median_floor = statistics.median(floors) if floors else 0

    for s in strategies:
        min_budget = MIN_DAILY_MICROS
        if s.budget_type == BudgetType.lifetime and s.start_date and s.end_date:
            days = max(1, (s.end_date - s.start_date).days + 1)
            min_budget = MIN_DAILY_MICROS * days
        if s.budget_micros < min_budget:
            issues.append(_issue("error", "strategy", "BUDGET_BELOW_MIN",
                                 "Minimum budget is $50/day.", field=s.name))
        if s.end_date and s.end_date < s.start_date:
            issues.append(_issue("error", "strategy", "END_BEFORE_START",
                                 "End date is before the start date.", field=s.name))

        creatives = (
            await db.execute(
                select(Creative)
                .join(StrategyCreative, StrategyCreative.creative_id == Creative.id)
                .where(StrategyCreative.strategy_id == s.id)
            )
        ).scalars().all()
        if not creatives:
            issues.append(_issue("error", "strategy", "NO_CREATIVE",
                                 "Add at least one creative to this strategy.", field=s.name))
        elif not any(c.review_status == ReviewStatus.approved for c in creatives):
            issues.append(_issue("error", "strategy", "CREATIVE_NOT_APPROVED",
                                 "This strategy has no approved creative yet.", field=s.name))

        if s.bidding_mode == BiddingMode.manual and s.max_cpm_micros and s.max_cpm_micros < median_floor:
            issues.append(_issue("warning", "strategy", "MANUAL_CPM_BELOW_FLOOR",
                                 "Your max CPM is below the median inventory floor; delivery may suffer.",
                                 field=s.name))

        est = await estimate(db, campaign.goal, _strategy_to_dict(s))
        if est["deliverability"] == "insufficient":
            issues.append(_issue("warning", "strategy", "TARGETING_INSUFFICIENT",
                                 "Targeting is too narrow to spend the budget.", field=s.name))

    if campaign.goal == CampaignGoal.retargeting and not any(s.include_audience_ids for s in strategies):
        issues.append(_issue("error", "strategy", "RETARGETING_WITHOUT_WEB_AUDIENCE",
                             "Retargeting needs a web audience in at least one strategy."))
    if campaign.goal == CampaignGoal.abm and not any(s.include_audience_ids for s in strategies):
        issues.append(_issue("error", "strategy", "ABM_WITHOUT_COMPANY_AUDIENCE",
                             "ABM needs a company-list or firmographic audience."))

    return issues


def _strategy_to_dict(s: Strategy) -> dict:
    return {
        "budget_type": s.budget_type.value, "budget_micros": s.budget_micros,
        "start_date": s.start_date.isoformat() if s.start_date else None,
        "end_date": s.end_date.isoformat() if s.end_date else None,
        "dayparting": s.dayparting, "locations": s.locations,
        "interest_segment_ids": [str(i) for i in (s.interest_segment_ids or [])],
        "demographics": s.demographics, "placement_mode": s.placement_mode.value,
        "channel_ids": [str(c) for c in (s.channel_ids or [])],
        "device_types": s.device_types, "bidding_mode": s.bidding_mode.value,
        "max_cpm_micros": s.max_cpm_micros,
    }
