"""Pixels, event types, apps, raw events (docs/02 §Advertisers & tracking, §Delivery & measurement)."""
from __future__ import annotations

import datetime as dt
import enum
import uuid

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Identity, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class InstallMethod(str, enum.Enum):
    gtm = "gtm"
    shopify = "shopify"
    manual = "manual"
    s2s = "s2s"
    wordpress = "wordpress"
    wix = "wix"
    squarespace = "squarespace"
    woocommerce = "woocommerce"
    bigcommerce = "bigcommerce"
    ticketmaster = "ticketmaster"
    eventbrite = "eventbrite"


class PixelStatus(str, enum.Enum):
    not_installed = "not_installed"
    active = "active"
    stale = "stale"


class EventType(str, enum.Enum):
    page_view = "page_view"
    lead = "lead"
    add_to_cart = "add_to_cart"
    purchase = "purchase"
    signup = "signup"
    custom = "custom"


class Platform(str, enum.Enum):
    ios = "ios"
    android = "android"


class Mmp(str, enum.Enum):
    appsflyer = "appsflyer"
    adjust = "adjust"
    branch = "branch"
    kochava = "kochava"
    singular = "singular"
    airbridge = "airbridge"
    gamesight = "gamesight"


class AppStatus(str, enum.Enum):
    pending = "pending"
    connected = "connected"
    error = "error"


class EventSource(str, enum.Enum):
    pixel = "pixel"
    mmp = "mmp"
    s2s = "s2s"


def _enum(e, name):
    return Enum(e, name=name, values_callable=lambda x: [m.value for m in x])


class Pixel(TimestampMixin, Base):
    __tablename__ = "pixels"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    advertiser_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("advertisers.id", ondelete="CASCADE"), unique=True
    )
    public_key: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    install_method: Mapped[InstallMethod] = mapped_column(_enum(InstallMethod, "install_method"))
    status: Mapped[PixelStatus] = mapped_column(_enum(PixelStatus, "pixel_status"), default=PixelStatus.not_installed)
    last_event_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class PixelEventType(Base):
    __tablename__ = "pixel_event_types"

    id: Mapped[uuid.UUID] = uuid_pk()
    pixel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pixels.id", ondelete="CASCADE"), index=True)
    event: Mapped[EventType] = mapped_column(_enum(EventType, "event_type"))
    custom_name: Mapped[str | None] = mapped_column(String(80))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class App(TimestampMixin, Base):
    __tablename__ = "apps"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    advertiser_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("advertisers.id", ondelete="CASCADE"), index=True)
    platform: Mapped[Platform] = mapped_column(_enum(Platform, "platform"))
    store_url: Mapped[str | None] = mapped_column(String(1000))
    bundle_id: Mapped[str | None] = mapped_column(String(200))
    mmp: Mapped[Mmp] = mapped_column(_enum(Mmp, "mmp"))
    mmp_app_id: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[AppStatus] = mapped_column(_enum(AppStatus, "app_status"), default=AppStatus.pending)
    last_postback_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    advertiser_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    source: Mapped[EventSource] = mapped_column(_enum(EventSource, "event_source"), default=EventSource.pixel)
    event: Mapped[str] = mapped_column(String(80))
    household_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    revenue_micros: Mapped[int] = mapped_column(BigInteger, default=0)
    order_id: Mapped[str | None] = mapped_column(String(120))
    url: Mapped[str | None] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(Text)
    lm_id: Mapped[str | None] = mapped_column(String(64), index=True)
    raw: Mapped[dict] = mapped_column(JSONB, default=dict)
