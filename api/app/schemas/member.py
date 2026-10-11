from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.identity import Role


class MemberOut(BaseModel):
    membership_id: uuid.UUID
    user_id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: Role
    created_at: datetime


class InviteRequest(BaseModel):
    email: EmailStr
    role: Role = Role.member


class InvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    role: Role
    token: str
    expires_at: datetime
    accepted_at: datetime | None
