"""AdCraft AI API entrypoint.

FastAPI app that also (later milestones) serves /px.js and /e (pixel ingest).
REST resources are mounted under /api/v1 (see docs/03-api-spec.md).
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html

from app.core.config import settings
from app.core.deps import require_non_production
from app.core.errors import UnhandledErrorMiddleware, install_error_handlers
from app.routers import (
    accounts,
    admin,
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
    # Docs are served by the guarded routes below (404 in production), not FastAPI's defaults.
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.get("/openapi.json", include_in_schema=False, dependencies=[Depends(require_non_production)])
async def openapi_json():
    return app.openapi()


@app.get("/docs", include_in_schema=False, dependencies=[Depends(require_non_production)])
async def swagger_ui():
    return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{settings.product_name} API")

# Order matters: the last middleware added is the outermost. The error net is added first so
# CORSMiddleware wraps it and error responses still carry CORS headers.
app.add_middleware(UnhandledErrorMiddleware)
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
app.include_router(admin.router, prefix=API_PREFIX)
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


_delivery_task: asyncio.Task | None = None


async def _delivery_loop() -> None:
    """Run delivery ticks forever (DELIVERY_LOOP=true). Free hosts have no separate worker
    process, so the API runs it; the advisory lock in delivery.tick keeps it to one at a time."""
    from app.core.db import SessionLocal
    from app.services import delivery

    log = logging.getLogger("app.delivery")
    while True:
        try:
            async with SessionLocal() as db:
                result = await delivery.tick(db)
            log.info("delivery tick: %s", result)
        except Exception:  # noqa: BLE001 — a bad tick must not kill the loop
            log.exception("delivery tick failed")
        await asyncio.sleep(settings.delivery_tick_seconds)


@app.on_event("startup")
async def _start_delivery_loop() -> None:
    global _delivery_task
    if settings.delivery_loop:
        _delivery_task = asyncio.create_task(_delivery_loop())


@app.on_event("shutdown")
async def _stop_delivery_loop() -> None:
    if _delivery_task:
        _delivery_task.cancel()


@app.on_event("startup")
async def _ensure_storage() -> None:
    try:
        from app.core.storage import ensure_bucket

        ensure_bucket()
    except Exception as e:  # noqa: BLE001 — MinIO may be down in some dev flows
        print(f"[startup] storage bucket init skipped: {e}")


@app.api_route("/health", methods=["GET", "HEAD"], tags=["meta"], summary="Liveness probe (used by docker healthcheck)")
async def root_health() -> dict[str, str]:
    return {"status": "ok"}
