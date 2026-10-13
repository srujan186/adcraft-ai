"""Platform admin tools for demos: backfill delivery history, reset the demo account.

Hidden unless ALLOW_SIMULATION=true *and* the caller's email is in ADMIN_EMAILS — anyone else
gets a plain 404 so the routes aren't advertised. Simulation only ever touches the caller's own
account, never other customers' campaigns.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.deps import Tenant, get_current_account, get_current_user
from app.core.errors import AppError
from app.models.identity import User
from app.services import delivery

router = APIRouter(prefix="/admin", tags=["admin"])


def require_platform_admin(user: User = Depends(get_current_user)) -> User:
    if not settings.allow_simulation or user.email.lower() not in settings.admin_email_set:
        raise AppError("NOT_FOUND", "Not found", 404)
    return user


class SimulateIn(BaseModel):
    days: int = Field(ge=1, le=60)


class DemoResetIn(BaseModel):
    password: str = Field(min_length=8, max_length=200)


@router.get("/status")
async def status(_: User = Depends(require_platform_admin)):
    return {
        "simulation": True,
        "delivery_loop": settings.delivery_loop,
        "sim_speed": settings.sim_speed,
        "tick_seconds": settings.delivery_tick_seconds,
    }


@router.post("/simulate", status_code=202)
async def simulate(body: SimulateIn, background: BackgroundTasks, _: User = Depends(require_platform_admin),
                   tenant: Tenant = Depends(get_current_account)):
    background.add_task(delivery.backfill, tenant.account.id, body.days)
    return {"started": True, "days": body.days, "account_id": str(tenant.account.id)}


@router.post("/demo-reset", status_code=202)
async def demo_reset(body: DemoResetIn, background: BackgroundTasks, _: User = Depends(require_platform_admin)):
    from app.services.demo import DEMO_EMAIL

    background.add_task(delivery.reset_demo, body.password)
    return {"started": True, "email": DEMO_EMAIL}
