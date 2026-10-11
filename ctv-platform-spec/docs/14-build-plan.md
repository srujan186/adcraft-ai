# 14 — Build plan (do milestones in order; each ends with green tests + checklist)

### M0 — Skeleton (½ day)
docker-compose (postgres, redis, minio, api, worker, scheduler, web), Makefile, FastAPI health, Next.js app with
design tokens (05), AppShell + TopNav with all nav items routing to placeholder pages, OpenAPI → TS client generation.
✅ `make dev` boots; nav works; `pnpm gen:api` produces types.

### M1 — Auth, accounts, advertisers, settings shell
Signup/login/refresh, memberships, X-Account-Id tenancy dep, members invite, advertisers CRUD, settings left nav with
all pages (empty states for unbuilt ones).
✅ Tenancy leakage test passes; create 2 advertisers; invite member.

### M2 — Seed data & taxonomy
`make seed`: households (07), channels (seed/channels.json → 560+ channels generated from the pattern + named
examples), interest tree (seed/interests.json), geos, companies. Endpoints /channels, /interest-segments, /geos/search.
✅ GET /interest-segments returns tree with reach; channel total reach ≈ 1.1B impressions/week label.

### M3 — Library & creatives
Upload flow, ffmpeg processing, automated review, Library page with labels & preview.
✅ Upload a 15s 1080p mp4 → approved; vertical mp4 → pillarboxed; 3s video → rejected with message.

### M4 — Campaign wizard (no publish yet)
Campaigns list (empty), create draft, 3-step wizard exactly per 06, strategies add/duplicate/delete, dayparting grid,
audience accordions, channel picker, bidding, creatives picker, estimator + EstimatePanel, validation endpoint,
Summary step. Save/dirty state, leave-confirm.
✅ Narrow targeting (single ZIP + 1 tiny interest) shows "Insufficient" + red card; Entire US shows Good/Excellent.

### M5 — Tracking
Pixel wizard (08), px.js, /e ingest, demo-store with dev household toolbar, App Tracking + MMP postback endpoint,
web audiences auto-created (Visitors/Leads/Purchasers), goal requirement checks wired into wizard step 1.
✅ Visiting demo-store marks Page View green in verify step; Sales goal stops showing "Pixel missing" after a purchase event.

### M6 — Audiences
Audiences page, custom audience sheet (contacts CSV, company list, firmographic, web traffic), lookalike, match
pipeline with match rate, Klaviyo/HubSpot/Mailchimp connectors behind a mock server in dev.
✅ Upload CSV of 1,000 synthetic emails/zips → match rate shown → usable in strategy include/exclude.

### M7 — Billing + publish
Balance, fake top-up, payment methods, transactions; publish flow, status machine, holdout assignment.
✅ Publish with $0 balance → INSUFFICIENT_BALANCE; after top-up → status learning.

### M8 — Delivery simulator + attribution + rollups
Simulator (07), bidder, pacing, frequency caps, learning-phase exploration, outcome simulation, attribution (08),
rollups (11), spend debits. Campaigns list metrics & chart, campaign detail, dashboard trends & status counts.
✅ `make simulate HOURS=168`: spend within ±5% of 7×daily budget; frequency caps respected; ROAS and CPS visible;
learning banner until day 14.

### M9 — Reports & Insights
Report builder, saved/scheduled reports, CSV, Insights Overview cards, Incrementality with eligibility + lift.
✅ Report Date × Channel × Sessions matches sum in campaign list for same range.

### M10 — Recommendations & Forecaster
Elasticity job, uplift benchmarks (seeded priors), recommendation generators, apply/reject/suppress/expire, dashboard
cards, ForecastChart with Current/Recommended/New + save.
✅ After 30 simulated days with budget-capped strategy → increase_budget card with projected uplift; apply changes budget;
reject with "on purpose" suppresses permanently.

### M11 — Ask Agent
SSE chat, context builder, tools, proposals with diff + apply, section popovers with suggested questions, static
fallback without key.
✅ Reference behavior test in 10 passes (LLM output checked with a rubric test that asserts the 3 sections + offer).

### M12 — Studio
URL → script → TTS → render → creative; studio page with regenerate.
✅ Generating from the demo-store URL yields an approved 15s 1080p creative in < 2 min.

### M13 — Polish
Onboarding checklist logic, notifications, help articles (write ~15 short markdown articles mirroring the FAQ list in 04),
explainer dialog, empty states everywhere, loading skeletons, responsive down to 1024px, Playwright e2e of the
"Definition of done" journey in CLAUDE.md.
