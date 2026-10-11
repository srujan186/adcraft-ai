from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.audience import AudienceSource, AudienceStatus


class AudienceCreate(BaseModel):
    advertiser_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    source: AudienceSource
    definition: dict[str, Any] = Field(default_factory=dict)


class LookalikeCreate(BaseModel):
    advertiser_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    seed_audience_id: uuid.UUID
    size_pct: int = Field(default=5, ge=1, le=10)


class AudienceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    advertiser_id: uuid.UUID
    name: str
    source: AudienceSource
    status: AudienceStatus
    definition: dict
    uploaded_records: int
    matched_households: int
    match_rate: float | None
    last_synced_at: dt.datetime | None
    created_at: dt.datetime
