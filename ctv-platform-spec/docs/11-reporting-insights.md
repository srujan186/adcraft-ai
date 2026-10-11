# 11 — Reporting, Insights & Incrementality

## Rollups (`services/rollups.py`)
- `rollup_hourly` every simulated hour: aggregate impressions + conversions of that hour into `stats_hourly`.
- `rollup_daily` at 00:30 account-tz: build `stats_daily` incl. zip, age/gender, interest (an impression counts once
  for each matching interest segment of the household; mark interest metrics as "overlapping" in UI).
- `households_reached` for ranges > 1 day must be computed as distinct (use HyperLogLog via Postgres `hll`
  extension, or exact COUNT DISTINCT on impressions for MVP).

## Report builder (`/dashboard/reports`)
**Dimensions** (grouped exactly):
- Time: Date, Week, Month, Hour of day, Day of week
- Entities: Advertiser Name, Campaign Name, Campaign Goal, Strategy Name, Creative Name
- Inventory and Placement: Screen Type, Channel, Live Sport
- Event Source: Event Source, Event Source ID, Event Source Platform
- Geography: Region (State), Metro, City, ZIP, County, Congressional District
- Audience (Targeting/Segments): Age, Gender, Interests, Demographic, Website Audience, Custom Audience
**Metrics**: Spend, Impressions, Households, Frequency, CPM, Sessions, Cost per Session, Leads, CPL, Purchases,
CPP, Revenue, ROAS, Installs, CPI, Conversion rate, Avg lag (hours), Completed views (simulate 96% VCR), VCR.
Behavior: user ticks dims + metrics → **Run** → POST /reports/run (server builds a safe SQL from a whitelist;
max 5 dims, 100k rows, paginate 100). Save (name), Download CSV, **Schedule** (daily/weekly/monthly, recipients;
the scheduler emails a CSV link — in dev, write to MinIO and create a notification), Filters (advertiser, campaign,
goal, strategy, channel, state).

## Insights › Overview (per advertiser, date range)
| card | viz | data |
|---|---|---|
| Geographic heatmap | US choropleth by state, metric select (Impressions, Spend, Sessions, Conversions, ROAS) | stats_daily by state |
| Time performance | 7 × 24 heatmap (weekday × hour, advertiser tz) colored by conversion rate; toggle impressions | stats_hourly |
| Demographics | grouped bars age × gender, metric select | stats_daily |
| Inventory | table top 20 channels: impressions, spend, CPM, sessions, CPS, ROAS + share bar | stats_daily by channel |
| In-market & interests | horizontal bars top 15 segments by index (conv rate vs avg) | stats_daily by interest |
| Creative | table/cards per creative: thumbnail, impressions, visit rate, conversions, ROAS | stats_daily by creative |
Each card has an "i" tooltip and an empty state "No data available for the selected dates".

## Insights › Incrementality
- Eligibility (per advertiser): ≥ 28 days of delivery, ≥ $3,000 spend, ≥ 200 attributed conversions, holdout ≥ 5,000 HH.
  Not eligible → empty state + checklist with progress bars for each threshold.
- Method: compare conversion rate of exposed households vs holdout households (same targeting eligibility, never served)
  over the period: `lift = (cr_exposed − cr_holdout)/cr_holdout`, incremental conversions = (cr_exposed − cr_holdout) × exposed_HH,
  iROAS = incremental revenue / spend. 95% CI via bootstrap (1,000 resamples over households). Show: lift %, iROAS,
  incremental conversions, CI bar, and a weekly lift chart; label "Measured against a held-out control group".
