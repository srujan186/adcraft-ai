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

### P0-3 Estimate fails whenever specific channels are selected — fixed
- Root cause: `_placement()` divided by Postgres `SUM()` results, which arrive as `Decimal`; the share
  became a Decimal and `float * Decimal` raised `TypeError` in `compute_estimate`. The all-channels path
  returned a literal `1.0`, so only selected channels broke. The 500 then left Starlette's outermost
  layer as plain text **outside** CORSMiddleware, so the browser saw only "Failed to fetch".
- Fix: channel sums converted to float. New `UnhandledErrorMiddleware` installed *inside* CORS turns any
  unhandled exception into the JSON envelope (`INTERNAL_ERROR`, generic message; details logged, never
  sent). Wizard estimate panel now shows "Couldn't update estimate" + Try again, dims stale numbers,
  and ignores out-of-order responses.
- Tests: `api/tests/test_estimate_channels.py` (1 small / 1 large / 20 channels each < all; unhandled
  error → 500 JSON with CORS header, no internals), `web/e2e/estimate-panel.spec.ts` (server error and
  network failure shown; Try again recovers). All failed before the fix.
- Real-data check (563 seeded channels): all 112.3M; largest channel 15.2M; 20 channels 476K;
  smallest 3,953 — all HTTP 200. Staging: pending.

### P0-6 Unfinished pages visible to clients — fixed
- Root cause: six settings screens rendered `MilestonePlaceholder` ("… building in Mx") and were linked
  from the menu. API keys had a backend but a placeholder page — and the backend ignored scopes
  (every key was full admin) and never saved "last used" for read requests (no commit on GETs).
- Fix: `NEXT_PUBLIC_SHOW_UNFINISHED` flag (off by default) hides Integrations Marketplace, Installed
  integrations, Invoices, Receipts, Refer & earn and My applications from navigation; their URLs return
  a real HTTP 404 (`next.config` rewrite; shared list in `src/lib/unfinished-routes.ts`). New API keys
  page: create with name + access (Read only / Read and write), key shown once with Copy, list with
  access/created/last used, inline-confirmed revoke, usage example. Backend: scopes validated
  (`read`/`write`, default `read`) and enforced (read-only key → 403 `SCOPE_REQUIRED` on writes);
  last-used committed on every authenticated request.
- Tests: `api/tests/test_api_keys.py` (scope enforcement, validation, last-used on reads, revoke, legacy
  keys); `web/e2e/settings-unfinished.spec.ts` (no menu link shows "building in"; six URLs → 404; key
  create → shown once → used → last used → revoke → 401). Backend scope/last-used tests failed before.
- Decisions recorded in `docs/DECISIONS.md`. Staging: pending.
