# 00 — Product overview

## One-liner
Self-serve streaming-TV advertising for performance marketers: launch a TV campaign in 5 minutes from
$50/day, target households like you target on social, and measure visits, leads, purchases and app installs
like a performance channel.

## Personas
- **DTC marketer** (Shopify brand): wants ROAS / cost per purchase, retargeting of site visitors.
- **App marketer**: wants cost per install, in-app revenue via an MMP (AppsFlyer/Adjust/Branch...).
- **B2B marketer**: wants ABM — reach a list of target companies, measure leads.
- **Agency**: manages many *Advertisers* (clients) under one *Account*, multiple members.

## Object hierarchy (the core mental model)

```
Account (billing entity, members, API keys)
 └── Advertiser (a brand / client: name, website, industry, logo, timezone)
      ├── Pixel (web tracker)            ├── App (MMP-tracked mobile app)
      ├── Audiences (custom, web, lookalike, firmographic, CRM-synced)
      ├── Creatives (videos in the Library)
      └── Campaign (goal + KPI + attribution window)
           └── Strategy (= ad set: budget, schedule, dayparting, targeting, placement, bidding, creatives)
                └── delivery → Impressions → (attribution) → Conversions
```

## Campaign goals (exact set)
| Group | Goal | Primary outcome | KPI options | Required tracking |
|---|---|---|---|---|
| Performance | Awareness | impressions / households | CPM, Cost per household | none |
| Performance | Traffic | sessions | Cost per session (CPS), Cost per visit | pixel `page_view` |
| Performance | Leads | leads | Cost per lead (CPL) | pixel `page_view` + `lead` |
| Performance | Sales | purchases | Cost per purchase (CPP), ROAS | pixel `page_view` + `purchase` |
| Specialized | Retargeting | sessions | CPS, CPP, ROAS | pixel `page_view` (web audience) |
| Specialized | App Promotion | installs | Cost per install (CPI), ROAS | app tracking (MMP) |
| Specialized | ABM | reached accounts / leads | Cost per reached account, CPL | company list audience |

## Feature map (screens → docs)
| Area | Screens | Doc |
|---|---|---|
| Dashboard | onboarding checklist, 7-day trends, status counts, recommendations, forecaster, feed/FAQ | 04, 09 |
| Campaigns | list + chart, tabs Campaigns/Strategies/Creatives, wizard | 04, 06 |
| Audiences | list, new custom / lookalike, sources | 04, 02 |
| Library | creatives, labels, upload, Studio (AI video) | 12 |
| Reports | report builder (dimensions × metrics), save, schedule, download | 11 |
| Insights | Overview (geo heatmap, time, demo, inventory, interests, creative), Incrementality | 11 |
| Ask Agent | global side panel + per-section "Ask agent" buttons | 10 |
| Settings | General, Members, Advertisers, Integrations (marketplace, installed), Web Pixel, App Tracking, Balance & transactions, Payment methods, Invoices, Receipts, Coupons, Referral, My applications, API keys | 13 |

## Glossary
- **CTV/OTT** — ads on streaming apps on TVs. Not clickable; results measured via household IP matching.
- **Household (HH)** — unique IP-based household; the unit of reach.
- **CPM** — cost per 1000 impressions. **ROAS** — revenue / spend. **iROAS** — incremental ROAS vs control.
- **Attribution window** — time after an impression during which a site/app event is credited (1h–30d).
- **Strategy** — ad set inside a campaign; owns its own budget and targeting.
- **Learning phase** — first 14 days after launch (5 days after resume) where delivery explores.
- **Deliverability** — forecast of whether targeting is broad enough to spend the budget.
- **Match rate** — % of uploaded records matched to households.
