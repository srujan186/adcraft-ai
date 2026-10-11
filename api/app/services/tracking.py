"""Pixel creation, install snippet, and /e event ingest (docs/08)."""
from __future__ import annotations

import datetime as dt
import hashlib
import secrets
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.audience import Audience, AudienceMember, AudienceSource, AudienceStatus
from app.models.inventory import Household
from app.models.tracking import (
    EventSource,
    EventType,
    InstallMethod,
    Pixel,
    PixelEventType,
    PixelStatus,
)
from app.models.tracking import Event as EventModel

PEPPER = "lumen-dev-pepper"
DEFAULT_EVENTS = [EventType.page_view, EventType.lead, EventType.add_to_cart, EventType.purchase, EventType.signup]
WEB_AUDIENCES = [("Visitors", ["page_view"]), ("Leads", ["lead"]), ("Purchasers", ["purchase"])]


def ip_hash(ip: str) -> str:
    return hashlib.sha256((ip + PEPPER).encode()).hexdigest()


def snippet(public_key: str) -> str:
    api = settings.public_api_url
    return (
        "<script>!function(w,d,k){w.lumen=w.lumen||function(){(w.lumen.q=w.lumen.q||[]).push(arguments)};"
        f"var s=d.createElement('script');s.async=1;s.src='{api}/px.js';d.head.appendChild(s);"
        "w.lumen('init',k);w.lumen('track','page_view');}(window,document,'" + public_key + "');</script>"
    )


async def create_pixel(
    db: AsyncSession, account_id: uuid.UUID, advertiser_id: uuid.UUID, install_method: InstallMethod
) -> Pixel:
    pixel = Pixel(
        account_id=account_id, advertiser_id=advertiser_id,
        public_key="px_" + secrets.token_hex(12), install_method=install_method,
        status=PixelStatus.not_installed,
    )
    db.add(pixel)
    await db.flush()

    for ev in DEFAULT_EVENTS:
        db.add(PixelEventType(pixel_id=pixel.id, event=ev, enabled=True))

    for name, events in WEB_AUDIENCES:
        db.add(Audience(
            account_id=account_id, advertiser_id=advertiser_id, name=name,
            source=AudienceSource.web_traffic, status=AudienceStatus.ready,
            definition={"pixel_id": str(pixel.id), "events": events, "lookback_days": 30},
        ))
    await db.commit()
    await db.refresh(pixel)
    return pixel


async def ingest_event(
    db: AsyncSession, key: str, payload: dict, sim_household: str | None, client_ip: str, user_agent: str | None
) -> None:
    pixel = (await db.execute(select(Pixel).where(Pixel.public_key == key))).scalar_one_or_none()
    if pixel is None:
        return

    ev = str(payload.get("ev") or payload.get("event") or "page_view")

    household_id: uuid.UUID | None = None
    if sim_household:
        try:
            hid = uuid.UUID(sim_household)
            if await db.get(Household, hid):
                household_id = hid
        except ValueError:
            household_id = None
    if household_id is None:
        h = (
            await db.execute(select(Household.id).where(Household.ip_hash == ip_hash(client_ip)).limit(1))
        ).scalar_one_or_none()
        household_id = h

    now = dt.datetime.now(dt.timezone.utc)
    db.add(EventModel(
        ts=now, account_id=pixel.account_id, advertiser_id=pixel.advertiser_id, source=EventSource.pixel,
        event=ev, household_id=household_id, ip_hash=ip_hash(client_ip),
        revenue_micros=int(float(payload.get("value", 0)) * 1_000_000),
        order_id=payload.get("order_id"), url=payload.get("url"), user_agent=user_agent,
        lm_id=payload.get("lm_id"), raw=payload,
    ))
    pixel.last_event_at = now
    pixel.status = PixelStatus.active

    try:
        et = EventType(ev)
    except ValueError:
        et = EventType.custom
    row = (
        await db.execute(
            select(PixelEventType).where(PixelEventType.pixel_id == pixel.id, PixelEventType.event == et)
        )
    ).scalar_one_or_none()
    if row is not None:
        row.last_seen_at = now

    if household_id is not None:
        auds = (
            await db.execute(
                select(Audience).where(
                    Audience.advertiser_id == pixel.advertiser_id, Audience.source == AudienceSource.web_traffic
                )
            )
        ).scalars().all()
        for aud in auds:
            if ev in (aud.definition or {}).get("events", []):
                exists = await db.get(AudienceMember, {"audience_id": aud.id, "household_id": household_id})
                if exists is None:
                    db.add(AudienceMember(audience_id=aud.id, household_id=household_id))
                    aud.matched_households = (aud.matched_households or 0) + 1

    await db.commit()


async def pixel_status(db: AsyncSession, pixel: Pixel) -> dict:
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)
    types = (
        await db.execute(select(PixelEventType).where(PixelEventType.pixel_id == pixel.id))
    ).scalars().all()
    out = []
    for t in types:
        count = (
            await db.execute(
                select(func.count()).select_from(EventModel).where(
                    EventModel.advertiser_id == pixel.advertiser_id,
                    EventModel.event == t.event.value,
                    EventModel.ts >= since,
                )
            )
        ).scalar_one()
        out.append({
            "event": t.event.value, "enabled": t.enabled,
            "seen": count > 0, "count_24h": count,
            "last_seen_at": t.last_seen_at.isoformat() if t.last_seen_at else None,
        })
    return {"status": pixel.status.value, "last_event_at": pixel.last_event_at.isoformat() if pixel.last_event_at else None, "events": out}
