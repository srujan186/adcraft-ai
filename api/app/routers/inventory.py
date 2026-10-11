"""Public inventory & taxonomy endpoints (global, no account scope)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.inventory import Channel, ChannelCategory, Company, Geo, GeoType, InterestSegment
from app.schemas.inventory import ChannelOut, ChannelsResponse, CompanyOut, GeoOut, InterestSegmentNode

router = APIRouter(tags=["inventory"])


@router.get("/channels", response_model=ChannelsResponse)
async def list_channels(
    category: ChannelCategory | None = None,
    q: str | None = None,
    limit: int = Query(default=600, le=1000),
    db: AsyncSession = Depends(get_db),
) -> ChannelsResponse:
    stmt = select(Channel)
    if category is not None:
        stmt = stmt.where(Channel.category == category)
    if q:
        stmt = stmt.where(Channel.name.ilike(f"%{q}%"))
    stmt = stmt.order_by(Channel.reach_households.desc()).limit(limit)

    items = (await db.execute(stmt)).scalars().all()
    total_count = (await db.execute(select(func.count()).select_from(Channel))).scalar_one()
    all_apps = (await db.execute(select(func.coalesce(func.sum(Channel.reach_households), 0)))).scalar_one()

    return ChannelsResponse(
        items=[ChannelOut.model_validate(c) for c in items],
        count=len(items),
        total_count=total_count,
        all_apps_reach_households=int(all_apps),
    )


@router.get("/interest-segments", response_model=list[InterestSegmentNode])
async def interest_segments(db: AsyncSession = Depends(get_db)) -> list[InterestSegmentNode]:
    rows = (await db.execute(select(InterestSegment))).scalars().all()
    by_parent: dict = {}
    for r in rows:
        by_parent.setdefault(r.parent_id, []).append(r)

    def build(node: InterestSegment) -> InterestSegmentNode:
        kids = sorted(by_parent.get(node.id, []), key=lambda s: s.reach_households, reverse=True)
        return InterestSegmentNode(
            id=node.id,
            name=node.name,
            reach_households=node.reach_households,
            children=[build(k) for k in kids],
        )

    roots = sorted(by_parent.get(None, []), key=lambda s: s.reach_households, reverse=True)
    return [build(r) for r in roots]


@router.get("/geos/search", response_model=list[GeoOut])
async def geos_search(
    q: str = Query(min_length=1),
    type: GeoType | None = None,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[GeoOut]:
    stmt = select(Geo).where(or_(Geo.name.ilike(f"%{q}%"), Geo.code.ilike(f"%{q}%")))
    if type is not None:
        stmt = stmt.where(Geo.type == type)
    stmt = stmt.order_by(Geo.households.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [GeoOut.model_validate(g) for g in rows]


@router.get("/companies/search", response_model=list[CompanyOut])
async def companies_search(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[CompanyOut]:
    stmt = (
        select(Company)
        .where(or_(Company.name.ilike(f"%{q}%"), Company.domain.ilike(f"%{q}%")))
        .order_by(Company.name)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [CompanyOut.model_validate(c) for c in rows]
