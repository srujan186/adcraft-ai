"""Password hashing (argon2), JWT access/refresh tokens, API-key helpers."""
from __future__ import annotations

import datetime as dt
import secrets

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_ph = PasswordHasher(
    time_cost=settings.argon2_time_cost,
    memory_cost=settings.argon2_memory_kib,
    parallelism=settings.argon2_parallelism,
)
ALGO = "HS256"


# ── passwords ────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:  # malformed hash etc.
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """True when the hash was made with different cost settings than the current ones."""
    try:
        return _ph.check_needs_rehash(password_hash)
    except Exception:
        return False


# ── JWT ──────────────────────────────────────────────────────────────────────
def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def create_access_token(user_id: str) -> str:
    exp = _now() + dt.timedelta(minutes=settings.jwt_access_ttl_minutes)
    return jwt.encode({"sub": str(user_id), "type": "access", "exp": exp}, settings.jwt_secret, algorithm=ALGO)


def create_refresh_token(user_id: str) -> str:
    exp = _now() + dt.timedelta(days=settings.jwt_refresh_ttl_days)
    return jwt.encode(
        {"sub": str(user_id), "type": "refresh", "exp": exp, "jti": secrets.token_hex(8)},
        settings.jwt_secret,
        algorithm=ALGO,
    )


def decode_token(token: str, expected_type: str | None = None) -> dict:
    """Raises jwt.PyJWTError on invalid/expired tokens."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
    if expected_type and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"expected {expected_type} token")
    return payload


# ── API keys (lum_<prefix><secret>) ───────────────────────────────────────────
def generate_api_key() -> tuple[str, str, str]:
    """Return (full_key, prefix, key_hash). The full key is shown to the user once."""
    prefix = secrets.token_hex(4)  # 8 chars
    secret = secrets.token_urlsafe(24)
    full = f"lum_{prefix}{secret}"
    return full, prefix, _ph.hash(full)


def verify_api_key(full_key: str, key_hash: str) -> bool:
    try:
        return _ph.verify(key_hash, full_key)
    except Exception:
        return False
