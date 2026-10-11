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


@router.get("/health", response_model=HealthResponse, summary="API health + identity")
async def health() -> HealthResponse:
    return HealthResponse(status="ok", product=settings.product_name, version="0.1.0")
