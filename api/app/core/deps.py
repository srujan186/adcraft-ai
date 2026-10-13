"""Auth + multi-tenancy dependencies.

Two auth modes (docs/03-api-spec.md):
  • Bearer <jwt> + X-Account-Id   → a user acting inside one of their accounts
  • Bearer lum_<api_key>          → an account inferred from the key (no user)

`get_current_account` is the tenancy gate: every account-scoped query takes its
account_id from the returned Tenant, never from client input.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import decode_token, verify_api_key
from app.models.identity import Account, ApiKey, Membership, Role, User


@dataclass
class Tenant:
    account: Account
    role: Role
    user: User | None  # None when authenticated via API key


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError("UNAUTHENTICATED", "Missing bearer token", 401)
    return authorization.split(" ", 1)[1].strip()


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """JWT-only principal (used by /me and user-centric routes)."""
    token = _bearer(authorization)
    if token.startswith("lum_"):
        raise AppError("UNAUTHENTICATED", "API keys cannot access this endpoint", 401)
    try:
        payload = decode_token(token, expected_type="access")
    except jwt.PyJWTError:
        raise AppError("UNAUTHENTICATED", "Invalid or expired token", 401)
    user = await db.get(User, payload["sub"])
    if user is None:
        raise AppError("UNAUTHENTICATED", "User no longer exists", 401)
    return user


async def get_current_account(
    authorization: str | None = Header(default=None),
    x_account_id: str | None = Header(default=None, alias="X-Account-Id"),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    token = _bearer(authorization)

    # ── API-key mode ──────────────────────────────────────────────────────────
    if token.startswith("lum_"):
        prefix = token[4:12]
        rows = (await db.execute(select(ApiKey).where(ApiKey.prefix == prefix))).scalars().all()
        for key in rows:
            if key.revoked_at is None and verify_api_key(token, key.key_hash):
                key.last_used_at = dt.datetime.now(dt.timezone.utc)
                account = await db.get(Account, key.account_id)
                if account is None:
                    break
                return Tenant(account=account, role=Role.admin, user=None)
        raise AppError("UNAUTHENTICATED", "Invalid API key", 401)

    # ── JWT mode ──────────────────────────────────────────────────────────────
    try:
        payload = decode_token(token, expected_type="access")
    except jwt.PyJWTError:
        raise AppError("UNAUTHENTICATED", "Invalid or expired token", 401)

    user = await db.get(User, payload["sub"])
    if user is None:
        raise AppError("UNAUTHENTICATED", "User no longer exists", 401)
    if not x_account_id:
        raise AppError("ACCOUNT_REQUIRED", "X-Account-Id header is required", 400)

    membership = (
        await db.execute(
            select(Membership).where(
                Membership.user_id == user.id, Membership.account_id == x_account_id
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise AppError("FORBIDDEN", "You are not a member of this account", 403)

    account = await db.get(Account, membership.account_id)
    assert account is not None
    return Tenant(account=account, role=membership.role, user=user)


def require_roles(*roles: Role):
    """Dependency factory: assert the tenant's role is in `roles`."""

    async def _dep(tenant: Tenant = Depends(get_current_account)) -> Tenant:
        if tenant.role not in roles:
            raise AppError("FORBIDDEN", "Insufficient role for this action", 403)
        return tenant

    return _dep


def require_non_production() -> None:
    """Gate for developer-only routes and API docs: a plain 404 in production, so their
    existence isn't advertised."""
    from app.core.config import settings

    if settings.is_production:
        raise AppError("NOT_FOUND", "Not found", 404)
