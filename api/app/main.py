"""AdCraft AI API entrypoint.

FastAPI app that also (later milestones) serves /px.js and /e (pixel ingest).
REST resources are mounted under /api/v1 (see docs/03-api-spec.md).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import install_error_handlers
from app.routers import (
    accounts,
    advertisers,
    agent,
    audiences,
    auth,
    billing,
    campaigns,
    creatives,
    developer,
    files,
    health,
    inventory,
    members,
    recommendations,
    reports,
    stats,
    strategies,
    studio,
    track_public,
    tracking_admin,
)

app = FastAPI(
    title=f"{settings.product_name} API",
    version="0.1.0",
    description="Self-serve Connected-TV advertising platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

install_error_handlers(app)

API_PREFIX = "/api/v1"

# Resource routers (grows per milestone)
app.include_router(health.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(accounts.router, prefix=API_PREFIX)
app.include_router(members.router, prefix=API_PREFIX)
app.include_router(advertisers.router, prefix=API_PREFIX)
app.include_router(developer.router, prefix=API_PREFIX)
app.include_router(inventory.router, prefix=API_PREFIX)
app.include_router(creatives.router, prefix=API_PREFIX)
app.include_router(files.router, prefix=API_PREFIX)
app.include_router(campaigns.router, prefix=API_PREFIX)
app.include_router(strategies.router, prefix=API_PREFIX)
app.include_router(tracking_admin.router, prefix=API_PREFIX)
app.include_router(audiences.router, prefix=API_PREFIX)
app.include_router(billing.router, prefix=API_PREFIX)
app.include_router(stats.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(recommendations.router, prefix=API_PREFIX)
app.include_router(agent.router, prefix=API_PREFIX)
app.include_router(studio.router, prefix=API_PREFIX)
app.include_router(track_public.router)  # /px.js, /e, /mmp at root


@app.on_event("startup")
async def _ensure_storage() -> None:
    try:
        from app.core.storage import ensure_bucket

        ensure_bucket()
    except Exception as e:  # noqa: BLE001 — MinIO may be down in some dev flows
        print(f"[startup] storage bucket init skipped: {e}")


@app.get("/health", tags=["meta"], summary="Liveness probe (used by docker healthcheck)")
async def root_health() -> dict[str, str]:
    return {"status": "ok"}
