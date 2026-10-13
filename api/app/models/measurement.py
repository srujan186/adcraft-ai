"""Delivery & measurement (docs/02 §Delivery & measurement): impressions, conversions,
daily rollups. (holdout_households lives in billing.py.)"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Identity, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Impression(Base):
    __tablename__ = "impressions"
    # set-based attribution: a household's latest impression from an advertiser
    __table_args__ = (Index("ix_impressions_hh_adv_ts", "household_id", "advertiser_id", "ts"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    strategy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    creative_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    channel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    advertiser_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    device_type: Mapped[str] = mapped_column(String(12), default="tv")
    cost_micros: Mapped[int] = mapped_column(BigInteger)
    live_sport: Mapped[bool] = mapped_column(Boolean, default=False)


class Conversion(Base):
    __tablename__ = "conversions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    event_id: Mapped[int | None] = mapped_column(BigInteger, index=True)  # "already credited?" lookups
    impression_id: Mapped[int | None] = mapped_column(BigInteger)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    creative_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    channel_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    household_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    event: Mapped[str] = mapped_column(String(40))
    revenue_micros: Mapped[int] = mapped_column(BigInteger, default=0)
    lag_seconds: Mapped[int] = mapped_column(Integer, default=0)
    model: Mapped[str] = mapped_column(String(20), default="last_touch")


class StatsDaily(Base):
    __tablename__ = "stats_daily"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    advertiser_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    creative_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    channel_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    state: Mapped[str | None] = mapped_column(String(2))
    impressions: Mapped[int] = mapped_column(BigInteger, default=0)
    households_reached: Mapped[int] = mapped_column(BigInteger, default=0)
    spend_micros: Mapped[int] = mapped_column(BigInteger, default=0)
    sessions: Mapped[int] = mapped_column(BigInteger, default=0)
    leads: Mapped[int] = mapped_column(BigInteger, default=0)
    purchases: Mapped[int] = mapped_column(BigInteger, default=0)
    installs: Mapped[int] = mapped_column(BigInteger, default=0)
    revenue_micros: Mapped[int] = mapped_column(BigInteger, default=0)
