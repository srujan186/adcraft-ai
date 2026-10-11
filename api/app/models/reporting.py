"""Saved report definitions (docs/02 §Billing/misc)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class ReportDefinition(TimestampMixin, Base):
    __tablename__ = "report_definitions"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    dimensions: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    metrics: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    filters: Mapped[dict] = mapped_column(JSONB, default=dict)
    date_range: Mapped[dict] = mapped_column(JSONB, default=dict)
    schedule: Mapped[dict | None] = mapped_column(JSONB)
    recipients: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    last_run_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
