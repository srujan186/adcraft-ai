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

### P0-7 Branding and names — fixed (code); data cleanup in P0-9
- Root cause: real brands used as examples in customer-facing copy (URL hints "stripe.com", the API docs
  example business "Stripe", video-editor end-card placeholders "Nike, Inc."), in the ad-writer prompt
  ("You have written campaigns for Apple, Nike, Airbnb, and Coca-Cola" — a fabricated claim that could
  steer generated ads toward real brands) and in code comments. Studio would generate an ad from any URL.
- Fix: neutral examples (reserved `.example` domains, "Your Company"), brand-neutral prompt and comments.
  API and seed data were already clean (no matches). Studio: `DOMAIN_MISMATCH` / `WEBSITE_REQUIRED` gate on
  job creation; the Studio page prefills the advertiser's own website and explains the rule; advertisers
  without a website can add one inline (Settings → Advertisers).
- Tests: `api/tests/test_studio_domain.py` (own site + subdomains allowed; other sites, look-alike
  prefix/suffix, missing website refused; business-name-only allowed) — refusals failed before;
  `web/e2e/studio-own-site.spec.ts`. Repo scan (api, seed, playbook, web, backend services/routers):
  only functional identifiers remain — see `docs/DECISIONS.md`.
- Note: `backend/` (video generator) prompt changed → needs a push to the HF Space when deploying.
- Staging: pending.

### P0-5 Slow first load and placeholder header — fixed (code); keep-warm is an infra action
- Root cause: the account switcher rendered the invented name "Your account" until `/auth/me`
  answered (10–20 s on a sleeping Render instance); `/auth/me` had `retry: false`, so a gateway error
  while the server woke left the header blank until a manual reload; other queries retried once with
  no backoff; several pages showed a bare "Loading…".
- Fix: `Skeleton` component; account switcher shows a skeleton until the real account arrives; app-wide
  retry policy (`shouldRetry`/`retryDelay` in `lib/api/client.ts`): network errors, non-JSON gateway pages
  and `INTERNAL_ERROR` retry up to 4× with 1/2/4/8 s backoff, our own JSON errors (401/403/404/422) never;
  `/auth/me` loaded once and shared (5 min staleTime, React Query dedupes); skeletons replace "Loading…"
  on the auth gate, campaigns list, campaign page and wizard. Staying logged in on reload was fixed
  earlier (cross-site refresh token, commit 8d5893f).
- Tests: `web/e2e/loading.spec.ts` — slow `/auth/me` shows a skeleton and never "Your account"; two 503s
  then success still loads the account; warm reload of Campaigns shows real data in < 3 s and stays on
  the page. The first two failed before the fix. E2E config: 10 s assertion waits, 2 workers (on-demand
  dev compiles made 5 s waits flaky).
- **Owner action:** keep the API awake — UptimeRobot (free) HTTP monitor on
  `https://<api>/api/v1/health` every 5 min, or a paid instance. Code cannot prevent the free tier sleeping.
- Staging: pending.

### P0-1 Nothing ever delivers on the deployed app — fixed
- Root causes: (1) the simulator only ran from a developer CLI; the scheduler that should have ticked it was a
  stub. (2) Nothing ever advanced campaign status — publishing set Scheduled/Learning and campaigns stayed
  there forever (scheduled ones never started). (3) Attribution loaded every event and queried per event;
  rollups built every row in Python — far too slow to run continuously on a small instance. (4) Empty
  states told customers to "run the simulator".
- Fix:
  - `services/delivery.py`: each tick delivers the real time elapsed since the last tick × `SIM_SPEED`,
    catches up after the host slept (capped), advisory-locked; runs in the API when `DELIVERY_LOOP=true`
    (and in the compose scheduler). `sim_clock` table records the last tick.
  - `services/lifecycle.py`: Scheduled → Learning on the start date, Learning → Delivering when
    `learning_until` passes, → Completed after every strategy's end date.
  - Attribution and rollups are single SQL statements (10× faster locally on 40k impressions; identical
    output — equivalence tests keep the original implementations as references). New indexes for them.
  - Simulator: optional account scope and RNG; stochastic rounding so 5-minute ticks don't lose ~25% of spend.
  - `seed-demo` CLI + `services/demo.py`: "Demo Co" / Nimbus Goods (fictional, `nimbusgoods.example`),
    verified pixel, 3 rendered creatives, 3 campaigns published through the real publish path (Sales with
    prospecting + retargeting strategies, Traffic, Awareness), 30 days of history, statuses advanced,
    recommendations generated. Re-running replaces the account (incl. tables without FKs).
  - Admin page `/dashboard/admin` + `/api/v1/admin/*` (simulate N days for own account, reset demo),
    gated by `ALLOW_SIMULATION` + `ADMIN_EMAILS`; "Admin" appears in the account menu only for admins.
  - No customer-facing "simulator" copy; the pixel test store explains itself in production.
  - Library and wizard degrade gracefully when a creative's media file is gone (ephemeral host disk).
- Tests: `test_delivery.py` (real-time spend ≈ budget, catch-up cap, no double delivery, speed, lock,
  lifecycle), `test_attribution_sql.py` (equal to original attribution + rollups incl. edge cases),
  `test_demo.py` (every screen non-zero as the demo user; re-seed leaves no orphans), `test_admin.py`
  (hidden when off / from non-admins; own-account only; bounds), `web/e2e/admin.spec.ts`.
- Real-stack check (local, full catalogue): `seed-demo` in 31 s → 3 campaigns, 30 days, 464,448
  impressions, 4 recommendations. Logged in as the demo user: dashboard trend (~$387/day), all 3
  campaigns Delivering, campaign metrics, Insights (geo, inventory, demographics, interests, creative),
  Forecaster and recommendations all populated.
- Observed, not changed (outside P0 or needs your call): Sales ROAS 0.46× comes from the simulator's
  base conversion rates — realistic-looking but may read as "losing money" to a client (tuning is Phase 4
  valuation work); two recommendations both say "All channels — Entire US" (cards should name the
  campaign — Phase 3); "Last 7 days" ends on today's partial day, so the line drops at the end;
  the Forecaster curve is stair-stepped because projections round to 0.1 (Phase 4 forecaster).
- **Owner action (production):** on the API service set `DELIVERY_LOOP=true`; for admin tools set
  `ALLOW_SIMULATION=true` and `ADMIN_EMAILS=<your email>`; then run `seed-demo` (CLI against Neon, or
  Admin → Reset demo account). Staging: pending.

### P0-7 addendum — seeded channel names imitated real brands — fixed
- Found while checking the demo's Insights: "Pluto Free TV", "Spectrum Cable Apps", "Discovery Bros
  Network", "Magic Kingdom+", "SportsCenter Live" (a real show name), "StreamMax Originals" and others.
  The first P0-7 scan used exact words and missed near-names.
- Fix: 10 channels renamed to invented names in `seed/channels.json`; Alembic migration `b3e5f7a9c1d2`
  renames them in place in existing databases (ids kept — verified on the local DB).
- Test: `api/tests/test_seed_brands.py` checks seeded channel names and the filler word lists against a
  list of real media brands (failed on the old names).

### P0-2 — agent ignored the account and stated false facts — fixed (real-LLM check pending the key)
- Root cause: (1) the `anthropic` package was not installed or listed in `api/requirements.txt`, so the
  LLM path raised `ModuleNotFoundError` every time; (2) `answer()` swallowed that and fell back to a
  canned reply that told every user their "Visitors, Leads and Purchasers web audiences are your
  highest-intent viewers", with no pixel and no audiences; (3) even with the package, the context held
  only goal/KPI/window and two booleans, and the sync client ran inside async code with 1,024 tokens.
- Fix:
  - `services/agent.py` builds the context from live data: campaign (status, goal, KPI, target, window),
    pixel/app status and events seen in 7 days, every audience with its household count split into
    `usable` (≥ 1,000) and `too_small`, each strategy's budget, dates, bidding and max CPM, placement and
    channels, devices, locations, dayparting, interests, demographics, included/excluded audiences,
    creatives with review status, and its estimate; inventory median and cheapest CPM floors; publish
    validation issues; open recommendations; 14 days of delivered metrics.
  - Claude via `AsyncAnthropic`: `claude-opus-5-5`, adaptive thinking, `effort` from `AGENT_EFFORT`
    (medium), server-side fallbacks, refusal handled, constant system prompt (rules incl. the
    1,000-household rule), context in the user turn, last 12 messages of the thread as history.
  - No key, or any LLM error: "The assistant isn't available right now…" plus up to 3 help-centre
    links matched to the question. No facts, no proposals.
  - Proposals come from a `propose_change` tool (budget, max CPM, bidding mode, duplicate strategy), are
    checked against the context's strategy ids, and `apply` only writes those three strategy fields.
    Before, apply did `setattr` for any key in the stored patch (a planted `account_id` reached the DB).
  - Ask Agent panel renders the help links and no longer crashes when a send fails.
- Tests: `api/tests/test_agent_context.py` (plan draft: no pixel, no creative, no audiences, manual $3
  CPM → context says pixel none, no usable audiences, `$3.00` vs `$19.00` median floor, the three
  validation codes; sub-1,000 audiences not usable; other accounts' campaigns ignored; no-key and
  error paths state no facts; request shape; history; refusal; proposals and the apply allow-list),
  `api/tests/test_agent.py` (help slugs match `web/src/content/help.ts`), `web/e2e/agent-unavailable.spec.ts`.
  The old canned-answer rubric test was removed with the canned answer.
- Not verified: the two plan questions against the real model — no key is available locally and real
  calls cost money. **Owner action:** set `ANTHROPIC_API_KEY` on the API service (optional
  `ANTHROPIC_MODEL`, `AGENT_EFFORT`), redeploy (new dependency), then on staging ask the plan's draft
  "what audience should I target?" and "what is my max CPM and is it too low?".

### P0-9 — demo environment full of test data — command ready, production run is yours
- Cause: production shares one database with every test sign-up (e.g. the "Claude audit (test)"
  draft in "simple.co", the "vibe" advertiser). Nothing removed them.
- Fix: `python -m app.cli cleanup` lists every account as KEEP or DELETE with members, advertisers
  and campaigns, and deletes nothing. `--apply` deletes the DELETE accounts and every row they own
  (incl. tables without FKs: impressions, conversions, stats_daily, elasticities), then users left
  with no account. Kept: the demo account, accounts of `ADMIN_EMAILS` users, and `--keep EMAIL`.
  It refuses to run if the demo account doesn't exist yet. `seed-demo` now uses the same purge.
- Tests: `api/tests/test_cleanup.py` (dry run changes nothing; apply leaves only kept accounts and no
  orphan rows; refuses without a demo account); `test_demo.py` still passes on the shared purge.
- Local dry run: KEEP 3, DELETE 119 (all e2e sign-ups).
- **Owner action:** run `seed-demo` on production first, then
  `python -m app.cli cleanup` with `DATABASE_URL` pointed at Neon, read the list, and re-run with
  `--apply`. Taking a Neon branch/snapshot first makes it undoable.

### P0-2 addendum — Groq provider; the owner's pass/fail check run against the real model
- The re-check on the deployed app still showed canned answers because the deployed build predates
  P0-2 (not pushed yet). The owner also put a Groq key in `ANTHROPIC_API_KEY`, which Anthropic would
  reject.
- Change: the agent runs on Groq (`GROQ_API_KEY`, `openai/gpt-oss-120b`, the model `backend/` already
  uses) or Anthropic, whichever key is set. A `gsk_` key found in `ANTHROPIC_API_KEY` is used with Groq.
  Context JSON is compact (~490 tokens for the check draft). gpt-oss tended to answer with only a tool
  call, so the tool result is sent back once for a written answer. The prompt now separates saved
  audiences from interest/demographic filters, requires prospecting advice when there are none,
  covers narrow targeting, floors vs. expected CPM, other draft gaps, and forbids invented values
  and proposing changes the user didn't ask for.
- Real-model run (local stack, owner's Groq key; draft: Golf + female + 18-24 + $500k+, manual $3,
  no pixel, no creative, 0 channels selected), 3 runs:
  - Audience: says there are no saved audiences and no pixel so start with prospecting, quotes
    127k-191k households, suggests broadening gender/age/income while learning, mentions the $3 CPM
    and missing creative, offers the change.
  - Max CPM: states $3.00, below $13.82 cheapest / $23.92 median floor, recommends automatic bidding
    or about $26.64, offers the change.
  - "yes, switch it to automatic bidding": a proposal (manual -> automatic) with an explanation.
  - Not covered: it never mentioned "0 channels selected". Placement "selected" with no channels
    isn't a validation issue today (the estimator treats it as all channels); left for Phase 1.
  - "Soft preferences" isn't offered: `strategies.suggestions_enabled` is stored but nothing in the
    UI or estimator uses it, so the agent recommends broadening filters instead.
- Free-tier limit: ~8k tokens/minute per Groq account (shared with `backend/` if it uses the same
  account). Answers took 1-3 s; back-to-back questions took 18-31 s while the client waited out the limit.
- Tests: Groq request shape, tool call -> proposal with a second call for the text, failure notice,
  misplaced key routed to Groq. 110 API tests pass.
- **Owner action:** on Render set `GROQ_API_KEY` (move the key out of `ANTHROPIC_API_KEY`), then push
  and redeploy the branch; the re-check needs the new build.
