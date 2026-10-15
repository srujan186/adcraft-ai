"""Health + meta endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(tags=["meta"])


class HealthResponse(BaseModel):
    status: str
    product: str
    version: str


# HEAD too: uptime monitors (UptimeRobot) send HEAD and count a 405 as down.
@router.api_route("/health", methods=["GET", "HEAD"], response_model=HealthResponse, summary="API health + identity")
async def health() -> HealthResponse:
    return HealthResponse(status="ok", product=settings.product_name, version="0.1.0")
