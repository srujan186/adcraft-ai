# AdCraft AI — CTV advertising platform

Self-serve Connected-TV advertising, built from the spec in
[`ctv-platform-spec/`](./ctv-platform-spec). This is **the** AdCraft AI product
(not a separate app); the existing video pipeline in [`backend/`](./backend)
becomes the **Creative Studio** engine (M12). Product name is configurable via
`NEXT_PUBLIC_PRODUCT_NAME`.

## Layout (repo root)
```
api/        FastAPI + Postgres (SQLAlchemy async) + Arq worker + APScheduler   ← platform API
web/        Next.js 15 + React 19 + Tailwind v4 + shadcn/ui + TanStack Query   ← platform web
pixel/      tracking pixel source (M5)
seed/       channels, interest taxonomy, demo data
playbook/   wizard-warning / agent / recommender rules
docker-compose.yml          platform stack (postgres, redis, minio, api, worker, scheduler, web)
docker-compose.videoapp.yml legacy video-app self-host stack (backend+frontend+nginx)
backend/    existing video generator  → reused as the Creative Studio engine
frontend/   existing marketing/editor (Next 16)  → folded in over time
```

## Run it

Prereqs: Node 22, Python 3.13, Docker + Compose, ffmpeg, `pnpm` (`npm i -g pnpm`).
`make` isn't on Windows — use the identical `pnpm` scripts.

```bash
pnpm dev          # == docker compose up --build  (postgres, redis, minio, api, worker, scheduler, web)
#   web → http://localhost:3000   api → http://localhost:8000  (/docs, /openapi.json)
pnpm gen:api      # regenerate web/src/lib/api from the running API
pnpm test         # api pytest
```

Host ports: Postgres **5433**, Redis **6380** (remapped to avoid a local Postgres on 5432).

### Native dev (faster)
```bash
docker compose up -d postgres redis minio
cd api && venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
cd web && pnpm dev
```

## Build status — following `ctv-platform-spec/docs/14-build-plan.md`
- [x] **M0 — Skeleton**: compose, API health, Next shell with design tokens, full nav, OpenAPI→TS client.
- [x] **M1 — Auth, accounts, advertisers, settings**: JWT + argon2, tenancy dep + API keys, members/invite, advertisers CRUD. 17/17 API tests incl. tenancy-leakage; signup→dashboard E2E.
- [x] **M2 — Seed data & taxonomy**: `python -m app.cli seed` (deterministic, RNG 42) loads **200k households**, **563 channels** (total reach **1.14B**), **93** interest segments, **1,295** geos, **1,500** companies. Endpoints `/channels`, `/interest-segments`, `/geos/search`, `/companies/search`. 21/21 API tests.
- [x] **M3 — Library & creatives**: local storage backend, multipart upload, ffmpeg transcode-to-1080p + thumbnail + automated review (15s→approved, vertical→pillarboxed, 3s→rejected), Library page with preview. 24/24 API tests + upload E2E.
- [x] **M4 — Campaign wizard**: campaigns CRUD (+ default strategy), strategies CRUD/duplicate, deterministic estimator + /estimate, /validate. 3-step wizard with live estimate panel. Acceptance verified in-browser: Entire US→excellent, ZIP+tiny interest→Insufficient. 31/31 API tests.
- [x] **M5 — Tracking**: pixels + /px.js + /e ingest + /mmp postbacks, web audiences auto-created, App Tracking, event-based goal checks. Web Pixel & App Tracking pages + demo store. Verified: page_view→seen, Sales MISSING_TRACKING clears after purchase. 36/36 API tests.
- [x] **M6 — Audiences**: CRUD, CSV upload with synthetic match rate, lookalike, refresh; Audiences page + wizard include/exclude. Acceptance: 1,000-row CSV → match rate → usable in a strategy. 38/38 API tests.
- [x] **M7 — Billing + publish**: balance, FakePaymentProvider top-up, payment methods, transactions, coupons; publish flow with INSUFFICIENT_BALANCE gate, status machine (learning/pause/resume), holdout assignment. Billing pages + wizard Publish. Acceptance: publish $0→INSUFFICIENT_BALANCE, after top-up→learning.
- [x] **M8 — Delivery simulator + attribution + rollups**: batch simulator (budget-paced, freq caps, holdouts), last-touch attribution, daily rollups, /stats/timeseries + /stats/table; campaign list metrics, dashboard trends, campaign detail. Acceptance: 168h sim → spend ±5%, freq caps respected, ROAS/CPS visible.
- [x] **M9 — Reports & Insights**: report builder (dims×metrics over stats_daily) + saved reports + CSV; Insights overview (geo/inventory/creative/demographics/interests) + incrementality eligibility. Acceptance: Date×Channel×Sessions report matches campaign-list sum.
- [x] **M10 — Recommendations & Forecaster**: elasticity fit (prior fallback), forecaster (recommended budget), recommendation generators (increase_budget, extend_window), apply/reject + suppression; dashboard rec cards + campaign forecaster. Acceptance: budget-capped→increase_budget→apply changes budget; reject "on purpose"→permanent suppression. 3/3 API tests.
- [x] **M11 — Ask Agent**: threads/messages/proposals, suggested questions, static playbook provider (+ optional Anthropic), Ask Agent side panel. Acceptance: reference-behavior rubric (3 sections + offer) passes. 3/3 API tests.
- [x] **M12 — Studio**: URL→script→render→approved creative (ffmpeg, silent-TTS fallback), studio jobs + Studio page with regenerate. Acceptance: generates an approved 15s 1080p creative. 2/2 API tests.
- [x] **M13 — Polish**: Help center (`/help` + statically-generated articles), dashboard onboarding checklist wired to real state + Learn feed. **Capstone — Definition-of-Done journey** verified end-to-end through the live API (signup → advertiser → pixel → events → Studio creative → campaign wizard → publish → 168h simulate → metrics → recommendations → forecast → agent). The journey surfaced and fixed a recommender bug (future-dated lagged-conversion rows displacing delivery days in the budget-pacing window); after the fix a 7-day sim produces the `increase_budget` recommendation. All backend tests pass.

**Done** — all milestones M0–M13 complete. Definition of done (CLAUDE.md): a new user signs up, creates an advertiser, installs the pixel, builds and publishes a campaign, runs the simulator, and sees impressions/households/sessions/conversions/ROAS across Campaigns, Reports and Insights; recommendations appear after ≥7 simulated days; the Ask Agent answers from live campaign context.

### Seeding
```bash
# native (infra in docker, seed via venv):
cd api && venv/Scripts/python.exe -m app.cli seed
# full docker stack:  docker compose exec api python -m app.cli seed
```
