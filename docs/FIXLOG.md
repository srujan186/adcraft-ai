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

### P0-8 Campaign name shown twice — fixed
- Root cause: the create page initialised the name field with the *value* "Untitled campaign", so
  clicking in and typing appended to it ("Untitled campaignClaude audit (test)").
- Fix: empty value + `placeholder="Untitled campaign"`; the API receives `name.trim() || "Untitled campaign"`.
- Tests: `web/e2e/campaign-name.spec.ts` (new Playwright suite, `pnpm e2e`) — typing "Spring Sale"
  gives exactly "Spring Sale" in the wizard header and the campaigns list; blank falls back.
  Failed before the fix with `You are creating… / Untitled campaignSpring Sale`.
- Existing bad names in production data are cleaned in P0-9. Staging: pending.
