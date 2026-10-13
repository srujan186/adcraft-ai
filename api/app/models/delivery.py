"""Delivery loop bookkeeping."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SimClock(Base):
    """When the delivery loop last ran (one row per loop). A server that slept catches up the
    gap from here on wake instead of losing those hours."""

    __tablename__ = "sim_clock"

    name: Mapped[str] = mapped_column(String(40), primary_key=True)
    last_tick_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
