"""Advertisers aggregate (docs/02-data-model.md §Advertisers & tracking).

Pixels / apps / pixel_event_types land in M5; only Advertiser is modelled in M1.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class Industry(str, enum.Enum):
    apps_gaming = "apps_gaming"
    ecommerce = "ecommerce"
    education_nonprofit = "education_nonprofit"
    automotive = "automotive"
    media_entertainment = "media_entertainment"
    legal = "legal"
    politics = "politics"
    home_improvement = "home_improvement"
    retail = "retail"
    b2b = "b2b"
    finance = "finance"
    health_wellness = "health_wellness"
    travel = "travel"
    food_bev = "food_bev"
    other = "other"


class Advertiser(TimestampMixin, Base):
    __tablename__ = "advertisers"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    website_url: Mapped[str | None] = mapped_column(String(1000))
    industry: Mapped[Industry] = mapped_column(
        Enum(Industry, name="industry", values_callable=lambda e: [m.value for m in e]),
        default=Industry.other,
    )
    logo_url: Mapped[str | None] = mapped_column(String(1000))
    timezone: Mapped[str] = mapped_column(String(64), default="America/New_York")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
