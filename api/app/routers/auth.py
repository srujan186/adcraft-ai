"""Auth & session: signup, login, refresh, logout, me."""
from __future__ import annotations

import datetime as dt

import jwt
from fastapi import APIRouter, Cookie, Depends, Header, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.identity import Account, Membership, Role, User
from app.schemas.account import AccountOut
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    MembershipOut,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "lumen_refresh"
REFRESH_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, user_id: str) -> str:
    """Issue a refresh token: set it as an httpOnly cookie (same-site deploys, local dev)
    and return it so the caller also puts it in the response body (cross-site deploys)."""
    token = create_refresh_token(user_id)
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.jwt_refresh_ttl_days * 86400,
        httponly=True,
        samesite="lax",
        secure=False,  # dev over http://localhost; set True behind TLS in prod
        path=REFRESH_PATH,
    )
    return token


async def _first_account_id(db: AsyncSession, user_id) -> str:
    row = (
        await db.execute(
            select(Membership.account_id).where(Membership.user_id == user_id).order_by(Membership.created_at)
        )
    ).first()
    if row is None:
        raise AppError("NO_ACCOUNT", "User has no account", 400)
    return str(row[0])


@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(body: SignupRequest, response: Response, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    existing = (await db.execute(select(User).where(User.email == body.email.lower()))).scalar_one_or_none()
    if existing is not None:
        raise AppError("EMAIL_TAKEN", "An account with this email already exists", 409)

    user = User(email=body.email.lower(), password_hash=hash_password(body.password), full_name=body.full_name)
    db.add(user)
    await db.flush()

    account = Account(name=body.company, onboarding={})
    db.add(account)
    await db.flush()

    db.add(Membership(account_id=account.id, user_id=user.id, role=Role.owner))
    user.last_login_at = dt.datetime.now(dt.timezone.utc)
    await db.commit()

    refresh_token = _set_refresh_cookie(response, str(user.id))
    return TokenResponse(
        access_token=create_access_token(str(user.id)), account_id=account.id, refresh_token=refresh_token
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = (await db.execute(select(User).where(User.email == body.email.lower()))).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise AppError("INVALID_CREDENTIALS", "Email or password is incorrect", 401)

    user.last_login_at = dt.datetime.now(dt.timezone.utc)
    account_id = await _first_account_id(db, user.id)
    await db.commit()

    refresh_token = _set_refresh_cookie(response, str(user.id))
    return TokenResponse(
        access_token=create_access_token(str(user.id)), account_id=account_id, refresh_token=refresh_token
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    body: RefreshRequest | None = None,
    db: AsyncSession = Depends(get_db),
    cookie_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
) -> TokenResponse:
    # Body first (cross-site deploys can't use the cookie), cookie as the fallback.
    token = (body.refresh_token if body else None) or cookie_token
    if not token:
        raise AppError("UNAUTHENTICATED", "No refresh token", 401)
    try:
        payload = decode_token(token, expected_type="refresh")
    except jwt.PyJWTError:
        raise AppError("UNAUTHENTICATED", "Invalid or expired refresh token", 401)

    user_id = payload["sub"]
    if await db.get(User, user_id) is None:
        raise AppError("UNAUTHENTICATED", "User no longer exists", 401)
    account_id = await _first_account_id(db, user_id)
    refresh_token = _set_refresh_cookie(response, user_id)
    return TokenResponse(access_token=create_access_token(user_id), account_id=account_id, refresh_token=refresh_token)


@router.post("/logout")
async def logout():
    r = Response(status_code=204)
    r.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)
    return r


@router.get("/me", response_model=MeResponse, tags=["auth"])
async def me(
    user: User = Depends(get_current_user),
    x_account_id: str | None = Header(default=None, alias="X-Account-Id"),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    rows = (
        await db.execute(
            select(Membership)
            .options(selectinload(Membership.account))
            .where(Membership.user_id == user.id)
            .order_by(Membership.created_at)
        )
    ).scalars().all()
    if not rows:
        raise AppError("NO_ACCOUNT", "User has no account", 400)

    memberships = [
        MembershipOut(account_id=m.account_id, account_name=m.account.name, role=m.role) for m in rows
    ]
    active = next((m.account for m in rows if str(m.account_id) == x_account_id), rows[0].account)

    return MeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        last_login_at=user.last_login_at,
        memberships=memberships,
        active_account=AccountOut.model_validate(active),
        onboarding=active.onboarding or {},
    )
