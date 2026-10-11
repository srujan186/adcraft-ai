# 09 — Recommendations & Performance Forecaster

Three layers of "strategy recommendation" (build in this order):
1. **Rules** (instant, in wizard) — playbook-driven warnings & defaults (06, playbook.yaml).
2. **Agent** (on demand) — LLM using playbook + live context (10).
3. **Data-driven recommendations** (daily job) — this doc.

## Recommendation cards
Shown on Dashboard and campaign detail. Card anatomy: type icon, title (e.g. "Increase budget on 'Prospecting – CA'"),
campaign name, one-sentence why, **projected outcome** chip ("+38% sessions · est. 120 → 166 / week"),
buttons **Apply** (primary) and **Reject** (ghost). If > 3 open, group by type with count; after all shown are
handled show "All done 🎉" confirmation + "Show next recommendations" if more exist.

### Types, triggers, actions
| type | trigger (evaluated daily, campaign out of learning, ≥ 7 days data) | action patch |
|---|---|---|
| increase_budget | strategy spends ≥ 95% of daily budget on ≥ 5 of last 7 days AND KPI at/under target AND reliable elasticity | budget → recommended budget from forecaster |
| expand_audience | deliverability limited/insufficient OR spend < 70% of budget for 5 days | enable suggestions, add top-3 interest segments by converter overlap |
| switch_to_auto_bidding | manual bidding AND win rate < 20% OR spend < 70% | bidding_mode=automatic |
| broaden_placement | selected channels < 20 AND spend < 70% | placement_mode=all |
| fix_tracking | goal requires events AND none seen in 72h | link to pixel setup (no auto-apply) — never expires |
| add_creative | single creative running ≥ 21 days AND CTR-proxy (visit rate) declining > 20% week-over-week | open Studio |
| split_retargeting_prospecting | strategy includes web audiences AND interest/demographic targeting | duplicate strategy into two |
| extend_attribution_window | window < 7d for sales/leads | window → 30d |

### Projected uplift (how numbers are computed)
- **Cross-advertiser uplift table** `uplift_benchmarks(type, goal, metric, median_uplift, p25, p75)` — recomputed
  daily from the last 6 months: for every applied recommendation (and every manual change of the same kind),
  compare the metric 14 days after vs 14 days before, normalized per $ where relevant. Seed with
  `playbook.yaml > uplift_priors` until n ≥ 30 per cell.
- **Budget** recommendations use the advertiser's own elasticity (below). If no reliable elasticity (r² < 0.5 or
  n_days < 14) → do not create a budget recommendation.

### Reject flow
Reject opens a small dialog with required reason (per type) + "Another reason" with optional one-line note:
- expand_audience: "My targeting is narrow on purpose", "I track results outside Lumen", "Not now", "Another reason"
- switch_to_auto_bidding: "I use manual bidding on purpose" (**account-wide suppression, permanent**), ...
- increase_budget: "Budget is capped", "Results not good enough yet", ...
Suppression rules: "on purpose" reasons → permanent; "Not now" → 30 days; default → 60 days; campaign-scoped unless noted.
Rejections cannot be undone in UI. Open recs expire after 90 days (except fix_tracking). Store reasons for analytics.

## Elasticity model (`elasticities` table, nightly)
Per (advertiser, goal) fit on daily points (spend_d, outcome_d) from the last 60 days, excluding learning days:
`outcome = alpha * spend^beta` (log-log OLS; beta ∈ (0,1] = diminishing returns). Store alpha, beta, r², n.

## Performance Forecaster (`GET /strategies/{id}/forecast`)
Available only for published strategies with ≥ 7 non-learning days and a reliable elasticity.
Returns curve points for budget from 0.25× to 4× current (40 points): `projected_outcome = alpha_s * b^beta`
where alpha_s is rescaled so the curve passes through the strategy's current 7-day average.
Outcome metric by goal: sessions (traffic, leads, retargeting), purchases (sales), installs (app), impressions (awareness).
**Recommended budget** = largest b where marginal efficiency `d outcome / d budget` ≥ 70% of efficiency at the
current budget (closed form: `b_rec = b_cur * 0.7^(1/(beta-1))`), capped at 3× current.
UI (ForecastChart): x = daily budget, y = projected outcome; three markers **Current**, **Recommended**, **New**
(draggable slider under the chart bound to the budget input). Shaded area beyond Recommended with label
"Scaling beyond recommended". Below chart: "At $X/day we project ~Y {outcome}/day (Z% vs current)". Save button
patches the strategy budget. If several strategies are ready, dashboard shows the one with the biggest projected gain.
