"""Developer settings: API keys + OAuth applications (account-scoped)."""
from __future__ import annotations

import datetime as dt
import secrets
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import Tenant, get_current_account, require_roles
from app.core.errors import AppError
from app.core.security import generate_api_key, hash_password
from app.models.identity import ApiKey, OAuthApp, Role
from app.schemas.developer import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyOut,
    OAuthAppCreate,
    OAuthAppCreated,
    OAuthAppOut,
)

router = APIRouter(tags=["developers"])


# ── API keys ──────────────────────────────────────────────────────────────────
@router.get("/api-keys", response_model=list[ApiKeyOut])
async def list_api_keys(
    tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)
) -> list[ApiKeyOut]:
    rows = (
        await db.execute(
            select(ApiKey).where(ApiKey.account_id == tenant.account.id).order_by(ApiKey.created_at)
        )
    ).scalars().all()
    return [ApiKeyOut.model_validate(k) for k in rows]


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(
    body: ApiKeyCreate,
    tenant: Tenant = Depends(require_roles(Role.owner, Role.admin)),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreated:
    full, prefix, key_hash = generate_api_key()
    key = ApiKey(
        account_id=tenant.account.id, name=body.name, prefix=prefix, key_hash=key_hash, scopes=body.scopes
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return ApiKeyCreated(**ApiKeyOut.model_validate(key).model_dump(), key=full)


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: uuid.UUID,
    tenant: Tenant = Depends(require_roles(Role.owner, Role.admin)),
    db: AsyncSession = Depends(get_db),
):
    key = await db.get(ApiKey, key_id)
    if key is None or key.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "API key not found", 404)
    key.revoked_at = dt.datetime.now(dt.timezone.utc)
    await db.commit()


# ── OAuth apps ("My applications") ──────────────────────────────────────────────
@router.get("/oauth-apps", response_model=list[OAuthAppOut])
async def list_oauth_apps(
    tenant: Tenant = Depends(get_current_account), db: AsyncSession = Depends(get_db)
) -> list[OAuthAppOut]:
    rows = (
        await db.execute(
            select(OAuthApp).where(OAuthApp.account_id == tenant.account.id).order_by(OAuthApp.created_at)
        )
    ).scalars().all()
    return [OAuthAppOut.model_validate(a) for a in rows]


@router.post("/oauth-apps", response_model=OAuthAppCreated, status_code=201)
async def create_oauth_app(
    body: OAuthAppCreate,
    tenant: Tenant = Depends(require_roles(Role.owner, Role.admin)),
    db: AsyncSession = Depends(get_db),
) -> OAuthAppCreated:
    client_id = secrets.token_hex(12)
    client_secret = secrets.token_urlsafe(32)
    app_row = OAuthApp(
        account_id=tenant.account.id,
        name=body.name,
        client_id=client_id,
        client_secret_hash=hash_password(client_secret),
        redirect_uris=body.redirect_uris,
    )
    db.add(app_row)
    await db.commit()
    await db.refresh(app_row)
    return OAuthAppCreated(**OAuthAppOut.model_validate(app_row).model_dump(), client_secret=client_secret)


@router.delete("/oauth-apps/{app_id}", status_code=204)
async def delete_oauth_app(
    app_id: uuid.UUID,
    tenant: Tenant = Depends(require_roles(Role.owner, Role.admin)),
    db: AsyncSession = Depends(get_db),
):
    app_row = await db.get(OAuthApp, app_id)
    if app_row is None or app_row.account_id != tenant.account.id:
        raise AppError("NOT_FOUND", "Application not found", 404)
    await db.delete(app_row)
    await db.commit()
