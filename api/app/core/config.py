"""Application configuration — all real settings read from env (see docs/01-architecture.md §Config)."""
from __future__ import annotations

from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# libpq-only params that asyncpg rejects (it would forward them as server settings).
_LIBPQ_ONLY = {"sslmode", "channel_binding"}


def _with_query(url: str, scheme: str, query: list[tuple[str, str]]) -> str:
    p = urlsplit(url)
    return urlunsplit((scheme, p.netloc, p.path, urlencode(query), p.fragment))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Core infra. Host ports are 5433/6380 (remapped in docker-compose to dodge a
    # local Postgres/Redis). In docker these are overridden to postgres:5432 / redis:6379.
    # "production" hides developer endpoints (/api/v1/dev/*) and the API docs. It is the
    # default so a deploy that forgets to set ENV fails closed; local dev and tests set
    # ENV=development.
    env: str = "production"

    database_url: str = "postgresql+asyncpg://lumen:lumen@localhost:5433/lumen"
    redis_url: str = "redis://localhost:6380/0"

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        """Accept a hosted provider's URL as given (Neon/Render/Supabase hand out
        `postgres://…?sslmode=require&channel_binding=require`) and turn it into the
        SQLAlchemy asyncpg form: `postgresql+asyncpg://…?ssl=require`."""
        q = parse_qsl(urlsplit(v).query)
        ssl = next((val for k, val in q if k == "sslmode"), None)
        q = [(k, val) for k, val in q if k not in _LIBPQ_ONLY]
        if ssl and ssl != "disable" and not any(k == "ssl" for k, _ in q):
            q.append(("ssl", "require"))
        return _with_query(v, "postgresql+asyncpg", q)

    @property
    def is_production(self) -> bool:
        return self.env.strip().lower() not in {"development", "dev", "local", "test"}

    @property
    def asyncpg_dsn(self) -> str:
        """Plain DSN for raw asyncpg.connect() (the seed CLI): libpq scheme and
        `sslmode=` — asyncpg's DSN parser does not understand `ssl=`."""
        q = parse_qsl(urlsplit(self.database_url).query)
        ssl = next((val for k, val in q if k == "ssl"), None)
        q = [(k, val) for k, val in q if k != "ssl"]
        if ssl:
            q.append(("sslmode", ssl))
        return _with_query(self.database_url, "postgresql", q)

    # Object storage (MinIO / S3)
    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "lumen"
    s3_access_key: str = "lumen"
    s3_secret_key: str = "lumen-secret"
    s3_region: str = "us-east-1"

    # Storage backend: "local" (dev default — no MinIO needed; served via /api/v1/files)
    # or "s3" (MinIO/S3 in prod).
    storage_backend: str = "local"
    storage_dir: str = "var/storage"

    # Auth
    jwt_secret: str = "dev-insecure-change-me"
    # Argon2id cost. OWASP's recommended minimum (m=19 MiB, t=2, p=1) instead of the
    # argon2-cffi defaults (64 MiB, t=3, p=4): ~5x less work. On a 0.1-CPU free host the
    # defaults made each login take ~4.5 s. Existing hashes keep verifying (params are
    # stored in the hash) and are upgraded on the next successful login.
    argon2_time_cost: int = 2
    argon2_memory_kib: int = 19456
    argon2_parallelism: int = 1
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 30

    # LLM (optional — agent is disabled with a friendly message when absent)
    anthropic_api_key: str | None = None

    # Simulator: 1 real minute == SIM_SPEED simulated minutes (60 => 1 min = 1 sim hour)
    sim_speed: int = 60

    # Creative Studio renderer:
    #   "simple"    — self-contained ffmpeg caption renderer (no external service)
    #   "video_app" — the full narrated generator in backend/ (Kokoro TTS + music + ffmpeg),
    #                 reached over HTTP at video_app_url. Requires a business URL.
    studio_renderer: str = "simple"
    video_app_url: str = "http://127.0.0.1:8001"

    # URLs
    public_api_url: str = "http://localhost:8000"
    product_name: str = "AdCraft AI"

    # CORS: comma-separated list of allowed web origins
    allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        # Browsers send Origin with no trailing slash, so "https://x.vercel.app/" would never
        # match; strip it (the most common way this setting gets pasted wrong).
        return [o.strip().rstrip("/") for o in self.allowed_origins.split(",") if o.strip().rstrip("/")]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
