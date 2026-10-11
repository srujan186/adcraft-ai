"""Application configuration — all real settings read from env (see docs/01-architecture.md §Config)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Core infra. Host ports are 5433/6380 (remapped in docker-compose to dodge a
    # local Postgres/Redis). In docker these are overridden to postgres:5432 / redis:6379.
    database_url: str = "postgresql+asyncpg://lumen:lumen@localhost:5433/lumen"
    redis_url: str = "redis://localhost:6380/0"

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
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
