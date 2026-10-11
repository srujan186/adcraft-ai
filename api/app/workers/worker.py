"""Arq worker — background jobs (video processing, audience matching, simulator ticks,
rollups, LLM jobs). M0: connects to Redis and registers only a no-op `ping`; each
milestone appends its job functions here.
Run: arq app.workers.worker.WorkerSettings
"""
from __future__ import annotations

from arq.connections import RedisSettings

from app.core.config import settings


async def ping(ctx: dict) -> str:
    return "pong"


async def startup(ctx: dict) -> None:
    print(f"[worker] {settings.product_name} worker online")


async def shutdown(ctx: dict) -> None:
    print("[worker] shutting down")


class WorkerSettings:
    functions = [ping]  # grows per milestone (M8 simulator, M6 matching, M9 reports, ...)
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
