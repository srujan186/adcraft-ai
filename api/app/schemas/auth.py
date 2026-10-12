from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.identity import Role
from app.schemas.account import AccountOut


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=200)
    company: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    account_id: uuid.UUID
    # Also returned in the body (not just the httpOnly cookie): when the web app and the
    # API are on different sites (Vercel + Render/HF), browsers won't store or send a
    # SameSite=Lax cookie cross-site, so the client keeps this and posts it to /refresh.
    refresh_token: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class MembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    account_id: uuid.UUID
    account_name: str
    role: Role


class MeResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    avatar_url: str | None
    last_login_at: datetime | None
    memberships: list[MembershipOut]
    active_account: AccountOut
    onboarding: dict
