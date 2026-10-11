"""Recommendations, suppressions, elasticities (docs/02 §Intelligence, docs/09)."""
from __future__ import annotations

import datetime as dt
import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class RecommendationType(str, enum.Enum):
    increase_budget = "increase_budget"
    expand_audience = "expand_audience"
    switch_to_auto_bidding = "switch_to_auto_bidding"
    broaden_placement = "broaden_placement"
    fix_tracking = "fix_tracking"
    add_creative = "add_creative"
    split_retargeting_prospecting = "split_retargeting_prospecting"
    extend_attribution_window = "extend_attribution_window"


class RecommendationStatus(str, enum.Enum):
    open = "open"
    applied = "applied"
    rejected = "rejected"
    expired = "expired"


def _enum(e, name):
    return Enum(e, name=name, values_callable=lambda x: [m.value for m in x])


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    type: Mapped[RecommendationType] = mapped_column(_enum(RecommendationType, "recommendation_type"))
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    projected: Mapped[dict] = mapped_column(JSONB, default=dict)
    action: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[RecommendationStatus] = mapped_column(
        _enum(RecommendationStatus, "recommendation_status"), default=RecommendationStatus.open, index=True
    )
    reject_reason: Mapped[str | None] = mapped_column(String(200))
    reject_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class RecommendationSuppression(Base):
    __tablename__ = "recommendation_suppressions"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    type: Mapped[RecommendationType] = mapped_column(_enum(RecommendationType, "recommendation_type"))
    until: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))  # null = permanent


class Elasticity(Base):
    __tablename__ = "elasticities"

    id: Mapped[uuid.UUID] = uuid_pk()
    advertiser_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    goal: Mapped[str] = mapped_column(String(30))
    alpha: Mapped[float] = mapped_column(Numeric(18, 6))
    beta: Mapped[float] = mapped_column(Numeric(10, 6))
    r2: Mapped[float] = mapped_column(Numeric(6, 4))
    n_days: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
