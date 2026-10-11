from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.advertiser import Industry


class AdvertiserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    website_url: str | None = Field(default=None, max_length=1000)
    industry: Industry = Industry.other
    logo_url: str | None = Field(default=None, max_length=1000)
    timezone: str = Field(default="America/New_York", max_length=64)


class AdvertiserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    website_url: str | None = Field(default=None, max_length=1000)
    industry: Industry | None = None
    logo_url: str | None = Field(default=None, max_length=1000)
    timezone: str | None = Field(default=None, max_length=64)


class AdvertiserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    website_url: str | None
    industry: Industry
    logo_url: str | None
    timezone: str
    archived_at: datetime | None
    created_at: datetime
