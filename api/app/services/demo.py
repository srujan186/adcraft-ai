"""A clean, fully populated demo account for client demos (fix plan P0-1 / P0-9).

"Demo Co" with one fictional advertiser (Nimbus Goods, e-commerce), a verified pixel, approved
creatives and three published campaigns — Sales (prospecting + retargeting strategies), Traffic and
Awareness — with `days` of delivery history, so every screen has data: campaigns out of learning,
a Forecaster with history, and recommendations.

Re-running replaces the previous demo account entirely (same login email).
"""
from __future__ import annotations

import datetime as dt
import random
import secrets
import uuid

from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.advertiser import Advertiser, Industry
from app.models.audience import Audience
from app.models.base import Base
from app.models.billing import TxnType
from app.models.campaign import (
    BudgetType,
    Campaign,
    CampaignGoal,
    Kpi,
    PlacementMode,
    Strategy,
    StrategyCreative,
)
from app.models.creative import Creative, CreativeSource, ReviewStatus
from app.models.identity import Account, Membership, Role, User
from app.models.tracking import Event, EventSource, InstallMethod, PixelEventType, PixelStatus
from app.services import lifecycle, recommender
from app.services.billing import adjust_balance
from app.services.publish import LEARNING_DAYS, publish_campaign
from app.services.simulator import simulate_all
from app.services.tracking import create_pixel

DEMO_EMAIL = "demo@adcraft-demo.com"
ACCOUNT = "Demo Co"
ADVERTISER = {"name": "Nimbus Goods", "website_url": "https://nimbusgoods.example", "industry": Industry.ecommerce,
              "timezone": "America/New_York"}
BALANCE_MICROS = 25_000_000_000  # $25,000 test-mode credit: 30 days of history + months of live delivery

CREATIVES = [  # (name, seconds, headline, call to action)
    ("Nimbus Goods — Everyday essentials", 15, "Everyday essentials, delivered", "Shop now"),
    ("Nimbus Goods — Free shipping", 15, "Free shipping over $50", "Shop the sale"),
    ("Nimbus Goods — New season", 30, "The new season is here", "See what's new"),
]

# (name, goal, kpi, attribution window h, [(strategy name, $/day, retargets site visitors?)])
CAMPAIGNS = [
    ("Nimbus — Sales", CampaignGoal.sales, Kpi.roas, 720,
     [("Prospecting — Entire US", 150, False), ("Retargeting — Site visitors", 60, True)]),
    ("Nimbus — Site traffic", CampaignGoal.traffic, Kpi.cps, 168, [("All channels — Entire US", 80, False)]),
    ("Nimbus — Brand awareness", CampaignGoal.awareness, Kpi.cpm, 168, [("All channels — Entire US", 100, False)]),
]


async def _delete_existing(db: AsyncSession, email: str) -> None:
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        return
    account_ids = (await db.execute(select(Membership.account_id).where(Membership.user_id == user.id))).scalars().all()
    for account_id in account_ids:
        # High-volume tables (impressions, conversions, stats_daily, …) carry account_id without a
        # foreign key, so cascading from accounts would orphan them: clear every account_id table.
        for table in reversed(Base.metadata.sorted_tables):
            if "account_id" in table.c and table.name != "accounts":
                await db.execute(delete(table).where(table.c.account_id == account_id))
        await db.execute(delete(Account).where(Account.id == account_id))
    await db.execute(delete(User).where(User.id == user.id))
    await db.commit()


async def _creatives(db: AsyncSession, account_id, advertiser_id, make_media: bool) -> list[Creative]:
    out = []
    for name, seconds, headline, cta in CREATIVES:
        fields: dict = {"duration_ms": seconds * 1000, "width": 1920, "height": 1080}
        if make_media:  # real, playable videos (needs ffmpeg); tests skip this
            from app.services.studio import render_creative

            r = await render_creative({"business_name": headline, "duration_s": seconds, "tone": "friendly", "cta": cta})
            fields = {"file_key": r["file_key"], "transcoded_key": r["file_key"], "thumbnail_key": r["thumbnail_key"],
                      "duration_ms": r["duration_ms"], "width": r["width"], "height": r["height"]}
        c = Creative(account_id=account_id, advertiser_id=advertiser_id, name=name, source=CreativeSource.studio,
                     review_status=ReviewStatus.approved, review_notes="Demo creative.", **fields)
        db.add(c)
        out.append(c)
    await db.flush()
    return out


async def seed_demo(
    db: AsyncSession,
    *,
    email: str = DEMO_EMAIL,
    password: str | None = None,
    days: int = 30,
    make_media: bool = True,
    now: dt.datetime | None = None,
) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    password = password or secrets.token_urlsafe(12)
    started = now - dt.timedelta(days=days)
    await _delete_existing(db, email)

    user = User(email=email, password_hash=hash_password(password), full_name="Demo User")
    account = Account(name=ACCOUNT, onboarding={})
    db.add_all([user, account])
    await db.flush()
    db.add(Membership(account_id=account.id, user_id=user.id, role=Role.owner))
    advertiser = Advertiser(account_id=account.id, **ADVERTISER)
    db.add(advertiser)
    await db.commit()
    await adjust_balance(db, account, BALANCE_MICROS, TxnType.topup, {"note": "Demo test-mode credit"})

    # Pixel installed and verified: the events Sales/Traffic need were seen recently.
    pixel = await create_pixel(db, account.id, advertiser.id, InstallMethod.manual)
    pixel.status, pixel.last_event_at = PixelStatus.active, now
    await db.execute(update(PixelEventType).where(PixelEventType.pixel_id == pixel.id).values(last_seen_at=now))
    for kind in ("page_view", "add_to_cart", "purchase"):
        db.add(Event(ts=now - dt.timedelta(minutes=5), account_id=account.id, advertiser_id=advertiser.id,
                     source=EventSource.pixel, event=kind, revenue_micros=85_000_000 if kind == "purchase" else 0,
                     url="https://nimbusgoods.example/", raw={"verification": True}))
    await db.commit()
    visitors = (await db.execute(select(Audience).where(Audience.advertiser_id == advertiser.id,
                                                        Audience.name == "Visitors"))).scalar_one()

    creatives = await _creatives(db, account.id, advertiser.id, make_media)
    await db.commit()

    campaigns = []
    for name, goal, kpi, window_h, strategies in CAMPAIGNS:
        c = Campaign(account_id=account.id, advertiser_id=advertiser.id, name=name, goal=goal, kpi=kpi,
                     attribution_window_hours=window_h, pixel_id=pixel.id)
        db.add(c)
        await db.flush()
        for s_name, per_day, retarget in strategies:
            s = Strategy(campaign_id=c.id, account_id=account.id, name=s_name, budget_type=BudgetType.daily,
                         budget_micros=per_day * 1_000_000, start_date=started.date(),
                         placement_mode=PlacementMode.all, include_audience_ids=[visitors.id] if retarget else [])
            db.add(s)
            await db.flush()
            for cr in creatives:
                db.add(StrategyCreative(strategy_id=s.id, creative_id=cr.id))
        await db.commit()
        await publish_campaign(db, c)  # the real publish path: validation, balance check, holdout
        campaigns.append(c)

    # Back-date the launch so the history below sits inside each campaign's life.
    for c in campaigns:
        c.published_at = started
        c.learning_until = started + dt.timedelta(days=LEARNING_DAYS)
    await db.commit()

    delivered = await simulate_all(db, days * 24, rng=random.Random(2026), account_id=account.id)
    statuses = await lifecycle.advance(db, now)
    recs = await recommender.generate_for_account(db, account.id)
    return {"email": email, "password": password, "account_id": str(account.id), "campaigns": len(campaigns),
            "days": days, "statuses": statuses, "recommendations": recs, **delivered}


async def demo_account_id(db: AsyncSession, email: str = DEMO_EMAIL) -> uuid.UUID | None:
    row = (await db.execute(text(
        "SELECT m.account_id FROM memberships m JOIN users u ON u.id = m.user_id WHERE u.email = :e LIMIT 1"
    ), {"e": email})).first()
    return row[0] if row else None
