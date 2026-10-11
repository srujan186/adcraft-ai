"""Account settings (General)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import Tenant, require_roles
from app.core.errors import AppError
from app.models.identity import Role
from app.schemas.account import AccountOut, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.patch("/{account_id}", response_model=AccountOut)
async def update_account(
    account_id: uuid.UUID,
    body: AccountUpdate,
    tenant: Tenant = Depends(require_roles(Role.owner, Role.admin)),
    db: AsyncSession = Depends(get_db),
) -> AccountOut:
    if account_id != tenant.account.id:
        raise AppError("FORBIDDEN", "Cannot modify another account", 403)
    if body.name is not None:
        tenant.account.name = body.name
    if body.timezone is not None:
        tenant.account.timezone = body.timezone
    await db.commit()
    await db.refresh(tenant.account)
    return AccountOut.model_validate(tenant.account)
