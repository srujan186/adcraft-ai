# Fix log — demo readiness (branch `fix/demo-readiness`)

Source plan: the "AdCraft AI — Fix & Update Plan" (live audit 2026-10-12/13). One row per item:
root cause → fix → test → verified on staging. An item is only "fixed" when a test covers it.

Staging: not yet provisioned (needs a separate Render service + Neon branch DB; Vercel builds a
preview from this branch automatically). Until then, items are verified locally against the full
stack and marked `staging: pending`.

## Phase 0 — Demo blockers

### P0-4 Developer endpoint and API docs exposed in production — fixed
- Root cause: `GET /api/v1/dev/households` (random household records) was registered unconditionally
  and only required a login; FastAPI served `/docs` and `/openapi.json` by default.
- Fix: `ENV` setting, **default `production`** (fails closed if unset). `require_non_production`
  dependency returns 404 for `/api/v1/dev/*`, `/docs` and `/openapi.json` in production. Local `.env`,
  docker-compose and the test suite set `ENV=development`.
- Tests: `tests/test_prod_guards.py` — 404 in production, 200 in development, default is production.
- Staging: pending. **Production needs nothing set** (default is production).
