# AdCraft AI — Repo Audit (task 00)

Produced before any v2 change. Maps what exists against `adcraft-v2-tasks/` (tasks 13/14
for UI, 01 for bugs) and the original `ctv-platform-spec/docs/03,04`. Decisions continue in
[`ctv-platform-spec/docs/DECISIONS.md`](../ctv-platform-spec/docs/DECISIONS.md).

Legend: ✅ implemented · 🟡 partial (note what's missing) · ❌ missing · 🧱 placeholder ("building in Mx").

---

## 1. Backend — routers (`api/app/routers/`)

| Router | Purpose | Status vs v2 |
|---|---|---|
| health | liveness | ✅ |
| auth | signup/login/refresh (JWT+argon2) | ✅ |
| accounts, members | account, membership, invite, API keys | ✅ (API-key scopes/last-used → task 14) |
| advertisers | CRUD + pixel create | 🟡 no logo/timezone/website/restricted-category (task 14, feeds task 03) |
| inventory | channels, interest-segments, geos, companies | ✅ (interest **tree w/ reach counts** for wizard → task 03/13) |
| creatives, files | upload, ffmpeg review, serve | ✅ (labels/pagination → task 13; B10 brand-name guard) |
| campaigns, strategies | CRUD, wizard, estimate, validate | 🟡 single-strategy wizard; many step-2 controls missing (task 13) |
| studio | URL→render→creative (video_app/simple) | 🟡 no voice/music/QR/business-name-only input (task 13) |
| track_public, tracking_admin | /px.js, /e, /mmp; pixel/app admin | 🟡 web-audience household resolution broken (B5); statuses wrong (B6) |
| audiences | CRUD, CSV, lookalike, match | 🟡 synthetic match; 0 matched HH for web audiences (B5); sources (task 13) |
| billing | balance, topup, coupons, methods | 🟡 no auto-recharge/invoices/receipts/refer (task 14) |
| stats, reports | timeseries, table, report builder | 🟡 limited dims; metric defs scattered (B3, task 02) |
| recommendations | list/apply/reject/recompute + forecast | 🟡 reliability gate weak (B8); DiD uplift missing (task 10) |
| agent | threads/messages/proposals, static+Anthropic | 🟡 no URL→campaign planner (task 11) |

Missing entirely: `api/app/strategy/` (valuation/pacing/pricing/exploration — tasks 03–08),
`api/app/metrics/definitions.py` (task 02, fixes B3), bid logs, experiments (task 12).

## 2. Web — routes (`web/src/app/`)
Marketing (`(marketing)`): `/`, `/generate`, `/result`, `/features|industries|solutions/[slug]`, `/resources/*` — ✅ (moved from `frontend/`).
Auth: `/login`, `/signup` — ✅. Dashboard: dashboard, campaigns (+[id], new, [id]/edit), audiences, library (+studio), reports, insights (overview, incrementality), settings/* — see §3/§4. Public: `/help(+[slug])`, `/demo-store` — ✅.

## 3. Screens vs task 13 (reference app)

**Dashboard** — 🟡 onboarding checklist ✅(basic); explainer/"Explain CTV" ❌; FAQ→agent cards ❌; forecaster card ❌; recs empty-state ❌; "Need help?" ❌; rec cards (projected chip/Why/another-reason/grouping) 🟡.
**Campaigns list** — 🟡 filter bar ❌; chart ❌; Campaigns|Strategies|Creatives tabs ❌; edit-columns/CSV/totals ❌; row kebab/bulk ❌; attribution-window override ❌. (metrics list ✅).
**Campaign detail** — 🟡 "Why isn't this delivering?" ❌(B2); pacing chart ❌; recall metric ❌; forecaster 🟡.
**Wizard step 1** — 🟡 KPI target + benchmarks ❌; attribution-window advanced ❌; missing-tracking for all goals 🟡(App Promotion gap, B-adjacent); use-cases/optimize panel ❌.
**Wizard step 2** — ❌ mostly: add/rename/dup/delete strategy ❌; schedule+dayparting grid 🟡(presets only); locations exclude/bulk-ZIP 🟡; interests tree+counts ❌; demographics (education/family/homeowner) ❌; custom/web-audience chips 🟡; placement grid 🟡; manual CPM+floor ❌; per-card Ask-agent ❌; estimate Weekly/Daily tabs 🟡.
**Wizard step 3** — 🟡 recap+edit links 🟡; errors/warnings list 🟡; balance check+Add funds 🟡; ad-policy checkbox ❌.
**Audiences** — 🟡 filters/columns/Manage ❌; multi-step new-audience sheet (all sources) ❌; lookalike sheet 🟡.
**Library & Studio** — 🟡 labels/pagination/row-actions ❌; Studio business-name input/voice/music/QR/regenerate-scene ❌.
**Reports** — 🟡 full dimension groups ❌(subset only); save/CSV ✅; schedule ❌.
**Insights** — 🟡 advertiser+range+window controls ❌(B4); heatmaps/demographics/inventory/interests/creative 🟡 (creative table needs B4 fix).
**Global** — 🟡 notifications dropdown ❌(bell unwired); help pages ✅; skeletons ❌(B9); responsive ≥1024 ✅.

## 4. Settings/billing/devs vs task 14
Working: General ✅, Members ✅, Advertisers 🟡(needs logo/tz/website/category), Web Pixel 🟡, App Tracking 🟡, Balance ✅, Payment methods ✅.
Placeholder (🧱, confirmed `building in`/coming-soon): Integrations Marketplace, Installed integrations, Invoices, Receipts, Refer & earn, My applications, API keys, Coupons.
Missing: auto-recharge, balance-empty→Blocked banner+auto-resume, OAuth app registration, `/api/docs` public, optional MCP server.

## 5. Algorithms — current implementation

| Component | File | Algorithm today | v2 target |
|---|---|---|---|
| Estimator | `services/estimator.py` | deterministic share-of-households reach, dynamic scale (NATIONAL_HH/live count), 4 deliverability bands | task 03/06 |
| Simulator/bidder | `services/simulator.py` | batch: serve impressions to `budget·hours/24` at avg inventory CPM, freq caps, holdouts, creative/channel rotation, write probable outcome events (base-rate) | tasks 04–08 (real valuation→pacing→pricing→exploration→bidder) |
| Pacing | — | none (flat target spend) | task 05 (PID) |
| Attribution | `services/attribution.py` | last-touch within window | task 02 |
| Rollups | `services/rollups.py` | aggregate impressions+conversions → `stats_daily` (keyed by event date → **future-dated conversion rows**) | task 02 |
| Recommender | `services/recommender.py` | log-log OLS elasticity (prior fallback β=0.6), triggers increase_budget/extend_window, reliability r²≥0.5 & n≥14 | tasks 09/10 (reliability gate B8, DiD uplift) |
| Forecaster | `services/recommender.py::forecast` | α·spend^β curve, ≥7 delivery days | task 09 |
| Agent | `services/agent.py` | static playbook + optional Anthropic Messages | task 11 (+planner) |
| Studio | `services/studio.py` | `video_app` (backend Kokoro+music+ffmpeg) or `simple` captions | task 13 polish |

## 6. Data integrity (task 01 bugs — code-level confirmation)

Per the v2 rule, the live numeric table (seed + `simulate HOURS=168`) is reproduced by **B1's test**
(`sum(transactions.spend)==sum(impressions.cost)==sum(stats_daily.spend)`), written first in task 01, rather than a
disruptive reseed of the active dev DB here. Root causes confirmed in code:

- **B1 spend mismatch** — `simulator.py` debits via `adjust_balance(-spend)` computed from summed `cost_micros`, but `rollups.rebuild_rollups` and the campaign-list stats are independent aggregations; no single source of truth. → derive transactions from hourly impression aggregates.
- **B2 delivery stalls** — batch sim has no scheduler/`sim:now`; `simulate_all` only runs on CLI; no watchdog/blocking-reason surface. 
- **B3 purchases 0 vs conversions 53** — no `metrics/definitions.py`; campaign page counts `event='purchase'` while incrementality counts attributed conversions. → single metric registry.
- **B4 Insights "No data"** — no advertiser/date-range control; `insights.py` date vs UTC and default range suspect.
- **B5 web audiences 0 matched** — `tracking.ingest_event` rarely resolves `household_id` (ip_hash match); audience members never populated for web traffic.
- **B6 wrong status labels** — StatusPill is untyped; audiences/pixel can render delivery-style labels. → typed enums per entity.
- **B7 wizard "Purchase ✓" vs verify** — `validation.py` requirement check and the verify panel read tracking differently. → both use `pixel_event_types.last_seen_at ≤7d`.
- **B8 rec/forecaster on learning w/ 0 purchases** — reliability gate (`r²≥0.5`) too weak; triggers don't enforce out-of-learning/≥7 non-learning-days/KPI-vs-target.
- **B9 loading race** — `/me` fetched per-component, not once in a provider; placeholder "Your account" shown.
- **B10 real brand names** — seeds/Studio names use real brands; Studio doesn't restrict generation to the advertiser's own domain.

## 7. Suggested sequencing
01 bugs (data integrity: B1,B3,B5 first) → 02 measurement (metric registry underpins B3/B4/reports/insights) → 03–08 strategy engine (port `reference/algorithms/*`) → 09–10 forecaster/recs (fixes B8) → 11 agent/planner → 12 experiments → 13/14 UI gaps → 15 real supply (flagged, needs owner sign-off). Commit per task; `make test` + web typecheck/lint each.
