# 01 — Architecture

## Stack (and why)
| Layer | Choice | Why / trade-off |
|---|---|---|
| Frontend | **Next.js 15 (App Router) + React 19 + TypeScript** | File-based routes map 1:1 to the screen list; SSR for marketing pages. |
| UI | **Tailwind CSS v4 + shadcn/ui (Radix)** | Matches the clean slate/indigo SaaS look; accessible primitives (Dialog, Sheet, Popover, Tabs). |
| Data fetching | **TanStack Query v5** + generated client (`openapi-typescript` + `openapi-fetch`) | Caching, optimistic updates, typed end-to-end. |
| Forms | **react-hook-form + zod** | Wizard has many nested forms; zod schemas mirror Pydantic. |
| Charts | **Recharts** (lines/bars/area), **react-simple-maps** (US heatmap) | Simple, enough for dashboards. |
| Tables | **TanStack Table v8** | Sorting, column chooser ("Edit columns"), totals row. |
| Backend API | **FastAPI + Pydantic v2 + SQLAlchemy 2 (async) + Alembic** | Team knows FastAPI; OpenAPI drives the TS client. |
| DB | **PostgreSQL 16** | Single DB for OLTP + MVP analytics (daily rollup tables). Upgrade path: ClickHouse for events. |
| Queue / jobs | **Redis + Arq** (async worker) + **APScheduler** process for cron | Simulator ticks, rollups, recommendation jobs, audience matching, scheduled reports. |
| Object storage | **MinIO** (S3 API) | Creatives, thumbnails, uploaded CSV lists, report exports. |
| Video | **ffmpeg** in worker | Transcode to 1920x1080 H.264 mp4, thumbnails, duration probe. |
| LLM | Anthropic Messages API (tool use) behind `LLMProvider` interface | Agent + creative script generation. Key in env `ANTHROPIC_API_KEY`. |
| TTS | `TTSProvider` interface; default implementation = silent track + captions (no key needed); optional ElevenLabs/OpenAI adapter | Keeps the project runnable offline. |
| Auth | Email+password (argon2) + JWT access (15m) / refresh (30d, httpOnly cookie); optional Google OAuth later | |
| Payments | `PaymentProvider` interface; default `FakePaymentProvider` (test mode) ; Stripe adapter optional | Prepaid balance model. |

## Repo layout
```
/api                      FastAPI app
  app/main.py
  app/core/{config,security,deps,db,tenancy}.py
  app/models/*.py         SQLAlchemy models (one file per aggregate)
  app/schemas/*.py        Pydantic
  app/routers/*.py        one router per resource (see 03-api-spec)
  app/services/
     estimator.py         audience size / deliverability (06)
     simulator/           supply adapter, bidder, pacer (07)
     attribution.py       (08)
     rollups.py           hourly/daily aggregates (11)
     recommender/         rules + uplift + elasticity (09)
     forecaster.py        (09)
     agent/               LLM agent, tools, playbook loader (10)
     studio/              AI creative generator (12)
     audiences/           matching, lookalike (02)
  app/workers/{worker.py,scheduler.py}
  alembic/
  tests/
/web                      Next.js app
  src/app/(marketing)/... public pages (minimal: landing, pricing)
  src/app/(auth)/login, signup
  src/app/dashboard/...  all app routes (see 04)
  src/app/demo-store/... fake e-commerce site with the pixel installed (for testing)
  src/components/ui/*    shadcn
  src/components/app/*   product components
  src/lib/api/*          generated client
/pixel                    pixel.js source (vanilla TS → bundled to /api/static/px.js)
/playbook/playbook.yaml
/seed/*.json
docker-compose.yml  Makefile
```

## Runtime processes
1. `api` — FastAPI (uvicorn), also serves `/px.js` and `/e` (pixel event ingest).
2. `worker` — Arq worker: video processing, audience matching, simulator ticks, rollups, LLM jobs.
3. `scheduler` — enqueues periodic jobs: `simulate_tick` (every 1 real minute = 1 simulated hour when `SIM_SPEED=60`), `rollup_hourly`, `recompute_recommendations` (daily), `expire_recommendations`, `run_scheduled_reports`, `update_campaign_statuses`.
4. `web` — Next.js.

## Tenancy
- `get_current_account` dependency resolves the JWT → user → active account (header `X-Account-Id`, user must be a member).
- Repository helpers always add `WHERE account_id = :account_id`. Write a pytest that hits every list endpoint with
  two accounts and asserts no leakage.

## Config (env)
`DATABASE_URL, REDIS_URL, S3_ENDPOINT, S3_BUCKET, JWT_SECRET, ANTHROPIC_API_KEY (optional; agent disabled with a friendly message if absent), SIM_SPEED=60, PUBLIC_API_URL, NEXT_PUBLIC_API_URL, NEXT_PUBLIC_PRODUCT_NAME=Lumen`.
