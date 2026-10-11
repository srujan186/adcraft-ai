"""Studio jobs (docs/02 §Creatives)."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class StudioJobStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    error = "error"


class StudioJob(TimestampMixin, Base):
    __tablename__ = "studio_jobs"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    advertiser_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("advertisers.id", ondelete="CASCADE"), index=True)
    input: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[StudioJobStatus] = mapped_column(
        Enum(StudioJobStatus, name="studio_job_status", values_callable=lambda x: [m.value for m in x]),
        default=StudioJobStatus.pending,
    )
    script: Mapped[dict | None] = mapped_column(JSONB)
    output_creative_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    error: Mapped[str | None] = mapped_column(Text)
