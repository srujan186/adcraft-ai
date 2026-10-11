"""Audiences (docs/02 §Audiences). Web audiences are auto-created with a pixel (M5);
custom / lookalike / firmographic + matching land in M6."""
from __future__ import annotations

import datetime as dt
import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class AudienceSource(str, enum.Enum):
    contacts_list = "contacts_list"
    company_list = "company_list"
    firmographic = "firmographic"
    web_traffic = "web_traffic"
    lookalike = "lookalike"
    api_upload = "api_upload"
    klaviyo = "klaviyo"
    hubspot = "hubspot"
    mailchimp = "mailchimp"
    customerio = "customerio"
    mparticle = "mparticle"
    tealium = "tealium"
    twilio = "twilio"
    fivetran = "fivetran"


class AudienceStatus(str, enum.Enum):
    processing = "processing"
    counting = "counting"
    ready = "ready"
    no_data = "no_data"
    error = "error"


def _enum(e, name):
    return Enum(e, name=name, values_callable=lambda x: [m.value for m in x])


class Audience(TimestampMixin, Base):
    __tablename__ = "audiences"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    advertiser_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("advertisers.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    source: Mapped[AudienceSource] = mapped_column(_enum(AudienceSource, "audience_source"))
    status: Mapped[AudienceStatus] = mapped_column(
        _enum(AudienceStatus, "audience_status"), default=AudienceStatus.processing
    )
    definition: Mapped[dict] = mapped_column(JSONB, default=dict)
    uploaded_records: Mapped[int] = mapped_column(Integer, default=0)
    matched_households: Mapped[int] = mapped_column(Integer, default=0)
    match_rate: Mapped[float | None] = mapped_column(Numeric(5, 4))
    last_synced_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class AudienceMember(Base):
    __tablename__ = "audience_members"

    audience_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("audiences.id", ondelete="CASCADE"), primary_key=True
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), primary_key=True
    )
