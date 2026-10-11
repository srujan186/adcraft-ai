# CLAUDE.md — Build instructions for "Lumen" (self-serve CTV advertising platform)

You are building a full-stack, self-serve Connected-TV (CTV / streaming TV) advertising platform.
The product is modelled on the UX and feature set of leading self-serve CTV platforms
(campaign wizard → strategies → AI recommendations → reporting). It is an original product:
**do not use any third-party brand name, logo, illustration, or marketing copy.** Product name is
`Lumen` (configurable via `NEXT_PUBLIC_PRODUCT_NAME`).

## Read these files in this order before writing code

| # | File | What it defines |
|---|------|-----------------|
| 1 | `docs/00-product-overview.md` | What the product does, personas, glossary |
| 2 | `docs/01-architecture.md` | Stack, services, repo layout, why each choice |
| 3 | `docs/02-data-model.md` | Every table, column, enum, index |
| 4 | `docs/03-api-spec.md` | Every REST endpoint, request/response shape |
| 5 | `docs/05-design-system.md` | Design tokens, typography, component rules |
| 6 | `docs/04-frontend-spec.md` | Every route and screen, layout, states |
| 7 | `docs/06-campaign-wizard.md` | Wizard logic, validation, live estimator |
| 8 | `docs/07-delivery-simulator.md` | Simulated ad exchange, bidder, pacing |
| 9 | `docs/08-tracking-attribution.md` | Pixel, events, attribution engine |
| 10 | `docs/09-recommendations-forecaster.md` | Recommendation engine, budget forecaster |
| 11 | `docs/10-ai-agent.md` | "Ask Agent" LLM agent, tools, playbook |
| 12 | `docs/11-reporting-insights.md` | Report builder, insights, incrementality |
| 13 | `docs/12-creative-studio.md` | Creative library, upload, AI video generator |
| 14 | `docs/13-integrations-billing-settings.md` | Settings, integrations, billing, API keys |
| 15 | `docs/14-build-plan.md` | Milestones, order of work, acceptance tests |
| — | `playbook/playbook.yaml` | Rules used by wizard warnings + agent + recommender |
| — | `seed/*.json` | Channels, interest taxonomy, demo data |

## Non-negotiable rules

1. **Follow `docs/14-build-plan.md` milestone by milestone.** Finish and test one milestone before the next.
   After each milestone: run backend tests, frontend typecheck + lint, and the milestone's acceptance checklist.
2. **The ad supply is simulated.** There is no real ad exchange. `docs/07-delivery-simulator.md` defines a
   `SupplyAdapter` interface; implement `SimulatedSupplyAdapter` only. Never call external ad networks.
3. **Money is stored as integer micros** (1 USD = 1_000_000 micros). Never floats for money.
4. **All timestamps UTC in DB**, converted to the advertiser's/location's timezone only in UI and in dayparting.
5. **Multi-tenant from day one:** every row that belongs to a customer has `account_id`; every query is scoped by it
   (enforce in a FastAPI dependency, see architecture doc).
6. **Type everything:** Pydantic v2 schemas on the backend; generate the TS client from OpenAPI
   (`pnpm gen:api`) — do not hand-write API types on the frontend.
7. **The LLM agent must never mutate data without returning a proposed diff first** (see `docs/10-ai-agent.md`).
8. When the spec is silent, pick the simplest option, write a one-line note in `docs/DECISIONS.md`, and continue.

## Commands (create these)

```bash
make dev          # docker compose up: postgres, redis, minio, api, worker, scheduler, web
make test         # pytest (api) + vitest (web)
make seed         # loads seed/*.json + demo account with 3 campaigns and 30 days of simulated delivery
make simulate     # runs the delivery simulator for N simulated hours: make simulate HOURS=24
pnpm gen:api      # regenerate web/src/lib/api from http://localhost:8000/openapi.json
```

## Definition of done (whole project)

- A new user can sign up, create an advertiser, install the pixel on the demo store (`/demo-store`),
  create a campaign through the 3-step wizard, publish it, run `make simulate`, and see impressions,
  households, sessions, conversions, ROAS in Campaigns, Reports and Insights.
- Recommendations appear on the dashboard after ≥ 7 simulated days, can be applied/rejected.
- The Budget Forecaster renders for a published strategy with ≥ 7 days of delivery.
- "Ask Agent" answers using live campaign context and can propose + apply changes after user confirmation.
