from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# "read" = GET requests only; "write" = also create/update/delete. Enforced in deps.
ApiKeyScope = Literal["read", "write"]


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    scopes: list[ApiKeyScope] = Field(default_factory=lambda: ["read"], min_length=1)

    @field_validator("scopes")
    @classmethod
    def _dedupe(cls, v: list[str]) -> list[str]:
        return sorted(set(v))


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    prefix: str
    scopes: list[str]
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class ApiKeyCreated(ApiKeyOut):
    key: str  # full key, returned once


class OAuthAppCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    redirect_uris: list[str] = Field(default_factory=list)


class OAuthAppOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    client_id: str
    redirect_uris: list[str]
    created_at: datetime


class OAuthAppCreated(OAuthAppOut):
    client_secret: str  # returned once
