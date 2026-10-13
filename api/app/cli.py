"""Seed & simulate CLI.

  python -m app.cli seed                 # load taxonomy + synthetic population (RNG seed 42)
  python -m app.cli simulate --hours N   # (M8) run the delivery simulator

Seeding is deterministic (random.Random(42)) and idempotent (truncates the
seeded, global tables first). Households are bulk-loaded with asyncpg COPY.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import random
import uuid
from pathlib import Path

import asyncpg

from app.core.config import settings

SEED_DIR = Path(__file__).resolve().parents[2] / "seed"
RNG_SEED = 42
SCALE_HOUSEHOLDS = 200_000
NATIONAL_HH = 120_000_000

DEVICE_WEIGHTS = {"mobile": 0.60, "tablet": 0.25, "desktop": 0.30}  # tv is always on


def _dsn() -> str:
    return settings.asyncpg_dsn


def _load(name: str) -> dict:
    return json.loads((SEED_DIR / name).read_text(encoding="utf-8"))


# ── interest taxonomy ──────────────────────────────────────────────────────────
def build_interest_rows(rng: random.Random):
    data = _load("interests.json")
    seg_rows = []  # (id, parent_id, name, reach)
    leaves = []  # (name, weight, parent_name)
    for seg in data["segments"]:
        pid = uuid.uuid4()
        preach = int(seg["reach_m"] * 1_000_000)
        seg_rows.append((pid, None, seg["name"], preach))
        for child in seg["children"]:
            creach = int(preach * rng.uniform(0.25, 0.7))
            seg_rows.append((uuid.uuid4(), pid, child, creach))
            leaves.append((child, creach, seg["name"]))
    return seg_rows, leaves, data["demographics"]


# ── channels ───────────────────────────────────────────────────────────────────
_FILLER_PREFIX = [
    "Nova", "Vertex", "Aurora", "Cedar", "Harbor", "Vista", "Echo", "Atlas", "Orbit", "Maple",
    "Granite", "Silver", "Crimson", "Lunar", "Pioneer", "Beacon", "Copper", "Delta", "Horizon",
    "Summit", "Ridge", "Cobalt", "Ember", "Quartz", "Terra", "Aspen", "Cascade", "Meridian",
]
_CAT_NOUN = {
    "entertainment": ["Entertainment", "Stream", "Shows", "Originals"],
    "news": ["News", "Report", "Daily", "Wire"],
    "sports": ["Sports", "Athletics", "GameDay", "Arena"],
    "kids": ["Kids", "Junior", "Cartoons", "Play"],
    "movies": ["Movies", "Cinema", "Films", "Picture"],
    "lifestyle": ["Lifestyle", "Living", "Home", "Style"],
    "music": ["Music", "Beats", "Sound", "Hits"],
    "spanish": ["Latino", "Español", "Mundo", "Vida"],
    "fast": ["Free TV", "Channel", "Network", "Now"],
}


def build_channel_rows(rng: random.Random):
    data = _load("channels.json")
    cpm = data["category_cpm_usd"]
    weights = data["category_weights"]
    total = data["total_channels"]
    rows = []  # (id, name, category, publisher, reach, cpm_micros, premium, logo)
    seen: set[str] = set()

    for ch in data["named"]:
        rows.append((
            uuid.uuid4(), ch["name"], ch["category"], None,
            int(ch["reach_m"] * 1_000_000), int(cpm[ch["category"]] * 1_000_000),
            bool(ch.get("premium", False)), None,
        ))
        seen.add(ch["name"])

    cats = list(weights.keys())
    cat_w = [weights[c] for c in cats]
    while len(rows) < total:
        cat = rng.choices(cats, weights=cat_w, k=1)[0]
        name = f"{rng.choice(_FILLER_PREFIX)} {rng.choice(_CAT_NOUN[cat])}"
        if name in seen:
            name = f"{name} {len(rows)}"
        seen.add(name)
        reach = int(max(40_000, rng.lognormvariate(math.log(530_000), 1.0)))
        base_cpm = int(cpm[cat] * 1_000_000 * rng.uniform(0.9, 1.15))
        rows.append((uuid.uuid4(), name, cat, None, reach, base_cpm, rng.random() < 0.05, None))
    return rows


# ── geos + per-state plan (shared with household generation) ────────────────────
def build_geo_plan(rng: random.Random):
    data = _load("geo_states.json")
    states = data["states"]
    metros = data["metros"]
    total_pop = sum(s["pop_m"] for s in states)

    dma_code_of = {}
    for i, m in enumerate(metros):
        dma_code_of[(m["city"], m["state"])] = str(500 + i)

    plan = {}  # code -> dict
    geo_rows = []  # (id, type, code, name, parent_id, households)
    country_id = uuid.uuid4()
    geo_rows.append((country_id, "country", "US", "United States", None, NATIONAL_HH))

    for si, s in enumerate(states):
        code, name = s["code"], s["name"]
        share = s["pop_m"] / total_pop
        hh = int(share * NATIONAL_HH)
        state_id = uuid.uuid4()
        geo_rows.append((state_id, "state", code, name, country_id, hh))

        state_metros = [m for m in metros if m["state"] == code] or [{"city": name, "state": code}]
        metro_entries = []
        for m in state_metros:
            dma_code = dma_code_of.get((m["city"], code), f"9{si:02d}")
            geo_rows.append((uuid.uuid4(), "city", m["city"], m["city"], state_id, int(hh * 0.25)))
            geo_rows.append((uuid.uuid4(), "dma", dma_code, f"{m['city']} DMA", state_id, int(hh * 0.3)))
            metro_entries.append({"city": m["city"], "dma_code": dma_code, "dma_name": f"{m['city']} DMA"})

        # ~50 sample households per zip so a single ZIP is genuinely narrow
        zbase = 10_000 + si * 1500
        n_zips = min(1400, max(12, round(share * 4000)))
        zips = sorted({f"{zbase + rng.randint(0, 1400):05d}" for _ in range(n_zips * 2)})[:n_zips]
        for z in zips:
            geo_rows.append((uuid.uuid4(), "zip", z, z, state_id, max(1000, hh // max(1, len(zips)))))

        counties = list({f"{m['city']} County" for m in state_metros})[:3] or [f"{name} County"]
        for c in counties:
            geo_rows.append((uuid.uuid4(), "county", c, c, state_id, int(hh * 0.2)))

        n_cd = max(1, round(share * 435))
        cds = [f"{code}-{i:02d}" for i in range(1, n_cd + 1)]
        for cd in cds:
            geo_rows.append((uuid.uuid4(), "congressional_district", cd, cd, state_id, int(hh / n_cd)))

        plan[code] = {
            "name": name, "tz": s["tz"], "weight": s["pop_m"],
            "metros": metro_entries, "zips": zips, "counties": counties, "cds": cds,
        }
    return plan, geo_rows


# ── households (synthetic population) ────────────────────────────────────────────
def build_household_rows(rng: random.Random, plan: dict, leaves: list, demo: dict):
    codes = list(plan.keys())
    weights = [plan[c]["weight"] for c in codes]
    leaf_names = [l[0] for l in leaves]
    leaf_w = [l[1] for l in leaves]
    leaf_parent = {l[0]: l[2] for l in leaves}

    ages = demo["age"]; genders = demo["gender"]; incomes = demo["income"]
    educations = demo["education"]; families = demo["family"]

    rows = []
    for i in range(SCALE_HOUSEHOLDS):
        code = rng.choices(codes, weights=weights, k=1)[0]
        sp = plan[code]
        metro = rng.choice(sp["metros"])
        n_int = rng.randint(3, 8)
        picks = set(rng.choices(leaf_names, weights=leaf_w, k=n_int))
        interests = sorted(picks | {leaf_parent[p] for p in picks})
        devices = ["tv"]
        for d, w in DEVICE_WEIGHTS.items():
            if rng.random() < w:
                devices.append(d)
        propensity = max(0.3, min(3.0, rng.lognormvariate(math.log(0.9), 0.6)))
        rows.append((
            uuid.uuid4(),
            hashlib.sha256(f"hh{i}".encode()).hexdigest(),
            rng.choice(sp["zips"]), metro["dma_code"], code, metro["city"],
            rng.choice(sp["counties"]), rng.choice(sp["cds"]), sp["tz"],
            rng.choice(ages), rng.choice(genders), rng.choice(incomes),
            rng.choice(educations), rng.choice(families), rng.random() < 0.64,
            None, interests, devices, int(propensity * 100),
        ))
    return rows


# ── companies (ABM / firmographic) ──────────────────────────────────────────────
_INDUSTRIES = ["software", "retail", "finance", "healthcare", "manufacturing", "media",
               "education", "real_estate", "logistics", "energy", "hospitality", "legal"]
_SIZES = ["1-10", "11-50", "51-200", "201-1000", "1001-5000", "5000+"]
_CO_PREFIX = ["Apex", "Blue", "Core", "Prime", "North", "Vertex", "Quanta", "Bright", "Iron",
              "Wave", "Pine", "Cloud", "Stark", "Orbit", "Delta", "Crest", "Fusion", "Nimbus"]
_CO_SUFFIX = ["Labs", "Systems", "Group", "Partners", "Industries", "Technologies", "Co", "Works",
              "Holdings", "Solutions", "Dynamics", "Networks"]


def build_company_rows(rng: random.Random, n: int = 1500):
    rows = []
    seen = set()
    while len(rows) < n:
        name = f"{rng.choice(_CO_PREFIX)} {rng.choice(_CO_SUFFIX)}"
        if name in seen:
            name = f"{name} {len(rows)}"
        seen.add(name)
        domain = name.lower().replace(" ", "") + ".com"
        rows.append((uuid.uuid4(), domain, name, rng.choice(_INDUSTRIES), rng.choice(_SIZES)))
    return rows


# ── orchestration ───────────────────────────────────────────────────────────────
async def seed() -> None:
    rng = random.Random(RNG_SEED)
    seg_rows, leaves, demo = build_interest_rows(rng)
    channel_rows = build_channel_rows(rng)
    plan, geo_rows = build_geo_plan(rng)
    household_rows = build_household_rows(rng, plan, leaves, demo)
    company_rows = build_company_rows(rng)

    conn = await asyncpg.connect(_dsn())
    try:
        await conn.execute(
            "TRUNCATE households, channels, interest_segments, geos, companies, "
            "company_households RESTART IDENTITY CASCADE"
        )
        await conn.copy_records_to_table(
            "interest_segments", records=seg_rows, columns=["id", "parent_id", "name", "reach_households"]
        )
        await conn.copy_records_to_table(
            "channels", records=channel_rows,
            columns=["id", "name", "category", "publisher", "reach_households", "base_cpm_micros",
                     "is_premium", "logo_url"],
        )
        await conn.copy_records_to_table(
            "geos", records=geo_rows, columns=["id", "type", "code", "name", "parent_id", "households"]
        )
        await conn.copy_records_to_table(
            "households", records=household_rows,
            columns=["id", "ip_hash", "zip", "dma_code", "state", "city", "county",
                     "congressional_district", "timezone", "age_bucket", "gender", "income_bucket",
                     "education", "family", "homeowner", "ethnicity_affinity", "interests",
                     "device_types", "propensity_x100"],
        )
        await conn.copy_records_to_table(
            "companies", records=company_rows, columns=["id", "domain", "name", "industry", "size_bucket"]
        )

        total_reach = await conn.fetchval("SELECT COALESCE(SUM(reach_households),0) FROM channels")
        print("[seed] complete")
        print(f"  interest_segments : {len(seg_rows)}")
        print(f"  channels          : {len(channel_rows)}  (total reach {float(total_reach)/1e9:.2f}B)")
        print(f"  geos              : {len(geo_rows)}")
        print(f"  households         : {len(household_rows)}")
        print(f"  companies         : {len(company_rows)}")
    finally:
        await conn.close()


async def simulate(hours: int) -> None:
    from app.services.simulator import simulate as run_sim

    result = await run_sim(hours)
    print(
        f"[simulate] {hours}h: campaigns={result['campaigns']} impressions={result['impressions']} "
        f"spend=${result['spend_micros'] / 1e6:,.2f} conversions={result['conversions']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed")
    sim = sub.add_parser("simulate")
    sim.add_argument("--hours", type=int, default=24)
    demo = sub.add_parser("seed-demo", help="create (or replace) the populated 'Demo Co' account")
    demo.add_argument("--email", default=None, help="login email (default demo@adcraft-demo.com)")
    demo.add_argument("--password", default=None, help="login password (random if omitted; printed once)")
    demo.add_argument("--days", type=int, default=30, help="days of delivery history to backfill")
    demo.add_argument("--no-media", action="store_true", help="skip rendering creative videos (no ffmpeg)")
    tick = sub.add_parser("tick", help="run one delivery tick (what DELIVERY_LOOP does every few minutes)")
    tick.set_defaults()
    clean = sub.add_parser("cleanup", help="list (or, with --apply, delete) every account except the demo account")
    clean.add_argument("--keep", action="append", default=[], metavar="EMAIL",
                       help="also keep the accounts this user belongs to (repeatable; ADMIN_EMAILS are always kept)")
    clean.add_argument("--apply", action="store_true", help="actually delete (default is a dry run)")
    args = parser.parse_args()

    if args.cmd == "seed":
        asyncio.run(seed())
    elif args.cmd == "simulate":
        asyncio.run(simulate(args.hours))
    elif args.cmd == "seed-demo":
        asyncio.run(_seed_demo(args))
    elif args.cmd == "tick":
        asyncio.run(_tick())
    elif args.cmd == "cleanup":
        asyncio.run(_cleanup(args))


async def _seed_demo(args) -> None:
    from app.core.db import SessionLocal
    from app.services.demo import DEMO_EMAIL, seed_demo

    async with SessionLocal() as db:
        r = await seed_demo(db, email=args.email or DEMO_EMAIL, password=args.password, days=args.days,
                            make_media=not args.no_media)
    print(f"[seed-demo] Demo Co ready: {r['campaigns']} campaigns, {r['days']} days, "
          f"{r['impressions']:,} impressions, {r['recommendations']} recommendations")
    print(f"[seed-demo] log in with  {r['email']}  /  {r['password']}")


async def _tick() -> None:
    from app.core.db import SessionLocal
    from app.services import delivery

    async with SessionLocal() as db:
        print(f"[tick] {await delivery.tick(db)}")


async def _cleanup(args) -> None:
    from app.core.config import settings
    from app.core.db import SessionLocal
    from app.services.cleanup import cleanup

    async with SessionLocal() as db:
        r = await cleanup(db, keep_emails=set(args.keep) | settings.admin_email_set, apply=args.apply)
    for label, rows in (("KEEP", r["keep"]), ("DELETE", r["delete"])):
        print(f"[cleanup] {label} {len(rows)} account(s)")
        for a in rows:
            print(f"  {a['name']}  ({', '.join(a['members']) or 'no members'})  created {a['created_at'][:10]}")
            if a["advertisers"]:
                print(f"    advertisers: {', '.join(a['advertisers'])}")
            if a["campaigns"]:
                print(f"    campaigns:   {', '.join(a['campaigns'])}")
    if r.get("error"):
        print(f"[cleanup] {r['error']}")
    elif r["applied"]:
        print(f"[cleanup] deleted {len(r['delete'])} account(s).")
    else:
        print("[cleanup] dry run - nothing deleted. Re-run with --apply to delete the accounts above.")


if __name__ == "__main__":
    main()
