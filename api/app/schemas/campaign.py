from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.campaign import (
    BiddingMode,
    BudgetType,
    CampaignGoal,
    CampaignStatus,
    Kpi,
    PlacementMode,
    StrategyStatus,
)


# ── campaigns ──────────────────────────────────────────────────────────────────
class CampaignCreate(BaseModel):
    advertiser_id: uuid.UUID
    name: str = Field(default="Untitled campaign", min_length=1, max_length=200)
    goal: CampaignGoal = CampaignGoal.traffic
    kpi: Kpi = Kpi.cps


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    goal: CampaignGoal | None = None
    kpi: Kpi | None = None
    kpi_target_micros: int | None = None
    kpi_target_ratio: float | None = None
    attribution_window_hours: int | None = Field(default=None, ge=1, le=720)
    pixel_id: uuid.UUID | None = None
    app_id: uuid.UUID | None = None


class StrategyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    campaign_id: uuid.UUID
    name: str
    budget_type: BudgetType
    budget_micros: int
    start_date: dt.date
    end_date: dt.date | None
    dayparting: dict
    frequency_cap: dict | None
    locations: dict
    interest_segment_ids: list[uuid.UUID]
    suggestions_enabled: bool
    demographics: dict
    include_audience_ids: list[uuid.UUID]
    exclude_audience_ids: list[uuid.UUID]
    placement_mode: PlacementMode
    channel_ids: list[uuid.UUID]
    device_types: list[str]
    live_sports_only: bool
    bidding_mode: BiddingMode
    max_cpm_micros: int | None
    status: StrategyStatus
    position: int


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    advertiser_id: uuid.UUID
    name: str
    goal: CampaignGoal
    kpi: Kpi
    kpi_target_micros: int | None
    kpi_target_ratio: float | None
    attribution_window_hours: int
    pixel_id: uuid.UUID | None
    app_id: uuid.UUID | None
    status: CampaignStatus
    blocked_reason: str | None
    created_at: dt.datetime


class CampaignDetail(CampaignOut):
    strategies: list[StrategyOut]


# ── strategies ──────────────────────────────────────────────────────────────────
class StrategyUpdate(BaseModel):
    name: str | None = None
    budget_type: BudgetType | None = None
    budget_micros: int | None = Field(default=None, ge=0)
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    dayparting: dict | None = None
    frequency_cap: dict | None = None
    locations: dict | None = None
    interest_segment_ids: list[uuid.UUID] | None = None
    suggestions_enabled: bool | None = None
    demographics: dict | None = None
    include_audience_ids: list[uuid.UUID] | None = None
    exclude_audience_ids: list[uuid.UUID] | None = None
    placement_mode: PlacementMode | None = None
    channel_ids: list[uuid.UUID] | None = None
    device_types: list[str] | None = None
    live_sports_only: bool | None = None
    bidding_mode: BiddingMode | None = None
    max_cpm_micros: int | None = None
    creative_ids: list[uuid.UUID] | None = None  # convenience: set strategy_creatives


# ── estimate ────────────────────────────────────────────────────────────────────
class EstimateRequest(BaseModel):
    goal: CampaignGoal
    strategy: dict[str, Any]


class RangeImps(BaseModel):
    impressions: list[int]
    households: list[int]


class EstimateResponse(BaseModel):
    audience_households: list[int]
    weekly: RangeImps
    daily: RangeImps
    deliverability: str
    expected_cpm_micros: int
    messages: list[str]


# ── validate ────────────────────────────────────────────────────────────────────
class Issue(BaseModel):
    level: str  # 'error' | 'warning'
    step: str
    field: str | None
    code: str
    message: str


class ValidateResponse(BaseModel):
    ok: bool
    issues: list[Issue]
