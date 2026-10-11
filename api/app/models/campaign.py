"""Campaigns & strategies (docs/02 §Campaigns)."""
from __future__ import annotations

import datetime as dt
import enum
import uuid

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_pk


class CampaignGoal(str, enum.Enum):
    awareness = "awareness"
    traffic = "traffic"
    leads = "leads"
    sales = "sales"
    retargeting = "retargeting"
    app_promotion = "app_promotion"
    abm = "abm"


class Kpi(str, enum.Enum):
    cpm = "cpm"
    cost_per_household = "cost_per_household"
    cps = "cps"
    cpv = "cpv"
    cpl = "cpl"
    cpp = "cpp"
    roas = "roas"
    cpi = "cpi"
    cost_per_account = "cost_per_account"


class CampaignStatus(str, enum.Enum):
    draft = "draft"
    in_review = "in_review"
    scheduled = "scheduled"
    learning = "learning"
    delivering = "delivering"
    paused = "paused"
    blocked = "blocked"
    completed = "completed"
    archived = "archived"


class BudgetType(str, enum.Enum):
    daily = "daily"
    lifetime = "lifetime"


class PlacementMode(str, enum.Enum):
    all = "all"
    selected = "selected"


class BiddingMode(str, enum.Enum):
    automatic = "automatic"
    manual = "manual"


class StrategyStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    completed = "completed"


def _enum(e, name):
    return Enum(e, name=name, values_callable=lambda x: [m.value for m in x])


class Campaign(TimestampMixin, Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    advertiser_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("advertisers.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    goal: Mapped[CampaignGoal] = mapped_column(_enum(CampaignGoal, "campaign_goal"))
    kpi: Mapped[Kpi] = mapped_column(_enum(Kpi, "kpi"))
    kpi_target_micros: Mapped[int | None] = mapped_column(BigInteger)
    kpi_target_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4))
    attribution_window_hours: Mapped[int] = mapped_column(Integer, default=720)
    app_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    pixel_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[CampaignStatus] = mapped_column(
        _enum(CampaignStatus, "campaign_status"), default=CampaignStatus.draft, index=True
    )
    blocked_reason: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    learning_until: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    strategies: Mapped[list["Strategy"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan", order_by="Strategy.position"
    )


class Strategy(TimestampMixin, Base):
    __tablename__ = "strategies"

    id: Mapped[uuid.UUID] = uuid_pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    budget_type: Mapped[BudgetType] = mapped_column(_enum(BudgetType, "budget_type"), default=BudgetType.daily)
    budget_micros: Mapped[int] = mapped_column(BigInteger, default=50_000_000)
    start_date: Mapped[dt.date] = mapped_column(Date, default=dt.date.today)
    end_date: Mapped[dt.date | None] = mapped_column(Date)
    dayparting: Mapped[dict] = mapped_column(JSONB, default=lambda: {"preset": "any", "grid": {}})
    frequency_cap: Mapped[dict | None] = mapped_column(JSONB)
    locations: Mapped[dict] = mapped_column(JSONB, default=lambda: {"include": [], "exclude": []})
    interest_segment_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    suggestions_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    demographics: Mapped[dict] = mapped_column(JSONB, default=dict)
    include_audience_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    exclude_audience_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    placement_mode: Mapped[PlacementMode] = mapped_column(
        _enum(PlacementMode, "placement_mode"), default=PlacementMode.all
    )
    channel_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    device_types: Mapped[list[str]] = mapped_column(ARRAY(String), default=lambda: ["tv"])
    live_sports_only: Mapped[bool] = mapped_column(Boolean, default=False)
    bidding_mode: Mapped[BiddingMode] = mapped_column(
        _enum(BiddingMode, "bidding_mode"), default=BiddingMode.automatic
    )
    max_cpm_micros: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[StrategyStatus] = mapped_column(
        _enum(StrategyStatus, "strategy_status"), default=StrategyStatus.draft
    )
    position: Mapped[int] = mapped_column(Integer, default=0)

    campaign: Mapped[Campaign] = relationship(back_populates="strategies")


class StrategyCreative(Base):
    __tablename__ = "strategy_creatives"

    strategy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), primary_key=True
    )
    creative_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("creatives.id", ondelete="CASCADE"), primary_key=True
    )
    weight: Mapped[int] = mapped_column(Integer, default=1)
