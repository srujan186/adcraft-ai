"""Account members + invitations."""
from __future__ import annotations

import datetime as dt
import secrets
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.deps import Tenant, get_current_account, require_roles
from app.core.errors import AppError
from app.models.identity import Invitation, Membership, Role
from app.schemas.member import InvitationOut, InviteRequest, MemberOut

router = APIRouter(prefix="/members", tags=["members"])


@router.get("", response_model=list[MemberOut])
async def list_members(
    tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)
) -> list[MemberOut]:
    rows = (
        await db.execute(
            select(Membership)
            .options(selectinload(Membership.user))
            .where(Membership.account_id == tenant.account.id)
            .order_by(Membership.created_at)
        )
    ).scalars().all()
    return [
        MemberOut(
            membership_id=m.id,
            user_id=m.user_id,
            email=m.user.email,
            full_name=m.user.full_name,
            role=m.role,
            created_at=m.created_at,
        )
        for m in rows
    ]


@router.post("/invite", response_model=InvitationOut, status_code=201)
async def invite_member(
    body: InviteRequest,
    tenant: Tenant = Depends(require_roles(Role.owner, Role.admin)),
    db: AsyncSession = Depends(get_db),
) -> InvitationOut:
    if body.role == Role.owner:
        raise AppError("INVALID_ROLE", "Cannot invite another owner", 400)
    inv = Invitation(
        account_id=tenant.account.id,
        email=body.email.lower(),
        role=body.role,
        token=secrets.token_urlsafe(24),
        expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=7),
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return InvitationOut.model_validate(inv)


@router.delete("/{membership_id}", status_code=204)
async def remove_member(
    membership_id: uuid.UUID,
    tenant: Tenant = Depends(require_roles(Role.owner, Role.admin)),
    db: AsyncSession = Depends(get_db),
):
    m = await db.get(Membership, membership_id)
    if m is None or m.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Member not found", 404)
    if m.role == Role.owner:
        raise AppError("FORBIDDEN", "Cannot remove the account owner", 403)
    await db.delete(m)
    await db.commit()
