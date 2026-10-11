"""Audience size / deliverability estimator (docs/06 §Estimator algorithm).

compute_estimate() is pure and unit-tested; estimate() wires it to the seeded
household population + channel CPMs.
"""
from __future__ import annotations

from sqlalchemy import and_, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import CampaignGoal
from app.models.inventory import Channel, Household, InterestSegment

NATIONAL_HH = 120_000_000
AVG_WEEKLY_IMPS_PER_HH = 3.2
FREQ = 2.4
DEFAULT_CPM_MICROS = 24_000_000

DEVICE_WEIGHTS = {"tv": 0.78, "mobile": 0.10, "desktop": 0.07, "tablet": 0.05}
GOAL_MULTIPLIER = {
    CampaignGoal.awareness: 1.0, CampaignGoal.traffic: 1.05, CampaignGoal.leads: 1.08,
    CampaignGoal.sales: 1.1, CampaignGoal.retargeting: 1.25, CampaignGoal.app_promotion: 1.1,
    CampaignGoal.abm: 1.15,
}
# rough share of weekly CTV viewing captured by each daypart preset
PRESET_SHARE = {
    "any": 1.0, "primetime": 0.28, "after_work": 0.30, "work_hours": 0.22,
    "sleeping": 0.06, "weekend": 0.30, "work_days": 0.72,
}
# hourly viewing weight (evening-heavy), index = hour 0..23
VIEWING_CURVE = [0.2, 0.15, 0.1, 0.1, 0.12, 0.2, 0.35, 0.5, 0.55, 0.6, 0.6, 0.6,
                 0.6, 0.6, 0.62, 0.65, 0.75, 0.9, 1.0, 1.0, 0.95, 0.85, 0.6, 0.4]

_LOC_COL = {
    "state": Household.state, "dma": Household.dma_code, "city": Household.city,
    "zip": Household.zip, "county": Household.county,
    "congressional_district": Household.congressional_district,
}


def device_share(device_types: list[str]) -> float:
    return sum(DEVICE_WEIGHTS.get(d, 0.0) for d in (device_types or ["tv"])) or DEVICE_WEIGHTS["tv"]


def daypart_share(dayparting: dict | None) -> float:
    if not dayparting:
        return 1.0
    preset = dayparting.get("preset", "any")
    if preset != "custom":
        return PRESET_SHARE.get(preset, 1.0)
    grid = dayparting.get("grid") or {}
    total = sum(VIEWING_CURVE) * 7
    sel = 0.0
    for _day, slots in grid.items():
        for slot in slots:
            sel += VIEWING_CURVE[(int(slot) // 2) % 24]
    return max(0.02, min(1.0, sel / total)) if total else 1.0


def _deliverability(ratio: float) -> str:
    if ratio < 0.5:
        return "insufficient"
    if ratio < 1.0:
        return "limited"
    if ratio < 3.0:
        return "good"
    return "excellent"


def _rng(v: float) -> list[int]:
    return [int(max(0, v * 0.8)), int(v * 1.2)]


def compute_estimate(
    *,
    eligible_sample: int,
    total_sample: int,
    placement_share: float,
    device_share_val: float,
    daypart_share_val: float,
    avg_cpm_micros: int,
    budget_daily_micros: int,
    goal: CampaignGoal,
) -> dict:
    scale = NATIONAL_HH / max(1, total_sample)
    eligible_national = eligible_sample * scale
    audience_hh = eligible_national * placement_share * device_share_val

    supply_week = audience_hh * AVG_WEEKLY_IMPS_PER_HH * daypart_share_val
    cpm_usd = (avg_cpm_micros / 1e6) * GOAL_MULTIPLIER.get(goal, 1.0)
    budget_daily_usd = budget_daily_micros / 1e6
    budget_week_imps = (budget_daily_usd * 7) / cpm_usd * 1000 if cpm_usd > 0 else 0.0

    imps = min(supply_week, budget_week_imps) if budget_week_imps else supply_week
    households = imps / FREQ
    ratio = (supply_week / budget_week_imps) if budget_week_imps > 0 else 999.0

    return {
        "audience_households": _rng(audience_hh),
        "weekly": {"impressions": _rng(imps), "households": _rng(households)},
        "daily": {"impressions": _rng(imps / 7), "households": _rng(households / 7)},
        "deliverability": _deliverability(ratio),
        "expected_cpm_micros": int(cpm_usd * 1e6),
        "messages": [],
    }


async def _eligible_sample(db: AsyncSession, strategy: dict) -> int:
    conds = []
    loc = strategy.get("locations") or {}
    inc = [i for i in loc.get("include", []) if i.get("type") in _LOC_COL]
    exc = [i for i in loc.get("exclude", []) if i.get("type") in _LOC_COL]
    if inc:
        conds.append(or_(*[_LOC_COL[i["type"]] == i["code"] for i in inc]))
    for i in exc:
        conds.append(not_(_LOC_COL[i["type"]] == i["code"]))

    seg_ids = strategy.get("interest_segment_ids") or []
    if seg_ids:
        names = (
            await db.execute(select(InterestSegment.name).where(InterestSegment.id.in_(seg_ids)))
        ).scalars().all()
        if names:
            conds.append(Household.interests.overlap(list(names)))

    demo = strategy.get("demographics") or {}
    demo_map = {
        "age": Household.age_bucket, "gender": Household.gender, "income": Household.income_bucket,
        "education": Household.education, "family": Household.family,
    }
    for key, col in demo_map.items():
        vals = demo.get(key)
        if vals:
            conds.append(col.in_(vals))

    stmt = select(func.count()).select_from(Household)
    if conds:
        stmt = stmt.where(and_(*conds))
    return (await db.execute(stmt)).scalar_one()


async def _placement(db: AsyncSession, strategy: dict) -> tuple[float, int]:
    """Return (placement_share, avg_cpm_micros)."""
    total_reach = (await db.execute(select(func.coalesce(func.sum(Channel.reach_households), 0)))).scalar_one()
    if strategy.get("placement_mode") == "selected" and strategy.get("channel_ids"):
        rows = (
            await db.execute(
                select(Channel.reach_households, Channel.base_cpm_micros).where(
                    Channel.id.in_(strategy["channel_ids"])
                )
            )
        ).all()
        sel_reach = sum(r[0] for r in rows) or 1
        share = min(1.0, sel_reach / total_reach) if total_reach else 1.0
        wcpm = sum(r[0] * r[1] for r in rows) / sel_reach if rows else DEFAULT_CPM_MICROS
        return share, int(wcpm)
    # all channels
    row = (
        await db.execute(
            select(func.coalesce(func.sum(Channel.reach_households * Channel.base_cpm_micros), 0),
                   func.coalesce(func.sum(Channel.reach_households), 0))
        )
    ).one()
    wcpm = int(row[0] / row[1]) if row[1] else DEFAULT_CPM_MICROS
    return 1.0, wcpm


def _budget_daily_micros(strategy: dict) -> int:
    budget = int(strategy.get("budget_micros") or 0)
    if strategy.get("budget_type") == "lifetime":
        start, end = strategy.get("start_date"), strategy.get("end_date")
        days = 1
        if start and end:
            import datetime as _dt

            try:
                s = _dt.date.fromisoformat(str(start))
                e = _dt.date.fromisoformat(str(end))
                days = max(1, (e - s).days + 1)
            except ValueError:
                days = 7
        else:
            days = 7
        return budget // days
    return budget


async def estimate(db: AsyncSession, goal: CampaignGoal, strategy: dict) -> dict:
    total = (await db.execute(select(func.count()).select_from(Household))).scalar_one()
    eligible = await _eligible_sample(db, strategy)
    placement_share, avg_cpm = await _placement(db, strategy)

    result = compute_estimate(
        eligible_sample=eligible,
        total_sample=total,
        placement_share=placement_share,
        device_share_val=device_share(strategy.get("device_types") or ["tv"]),
        daypart_share_val=daypart_share(strategy.get("dayparting")),
        avg_cpm_micros=avg_cpm,
        budget_daily_micros=_budget_daily_micros(strategy),
        goal=goal,
    )

    msgs: list[str] = []
    if result["deliverability"] == "insufficient":
        msgs.append(
            f"Your targeting is too narrow. Broaden your audience to improve delivery for your "
            f"{goal.value} campaign."
        )
    elif result["deliverability"] == "limited":
        msgs.append("Delivery may be limited. Consider broadening targeting or raising your budget.")
    if goal == CampaignGoal.retargeting and result["audience_households"][1] < 1000:
        msgs.append("Your web audience is too small. Retargeting needs a larger pool of site visitors.")
    result["messages"] = msgs
    return result
