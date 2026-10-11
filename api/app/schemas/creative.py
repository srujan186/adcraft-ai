from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.creative import CreativeSource, ReviewStatus


class UploadUrlRequest(BaseModel):
    filename: str
    content_type: str = "video/mp4"


class UploadUrlResponse(BaseModel):
    upload_url: str
    file_key: str


class CreativeCreate(BaseModel):
    advertiser_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    file_key: str


class CreativeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    labels: list[str] | None = None


class CreativeOut(BaseModel):
    id: uuid.UUID
    advertiser_id: uuid.UUID
    name: str
    source: CreativeSource
    review_status: ReviewStatus
    review_notes: str | None
    duration_ms: int | None
    width: int | None
    height: int | None
    size_bytes: int | None
    labels: list[str]
    created_at: datetime
    thumbnail_url: str | None = None
    video_url: str | None = None
