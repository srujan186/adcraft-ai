# 07 — Delivery simulator (simulated ad exchange, bidder, pacing)

Real CTV supply needs SSP/DSP contracts. This project ships a **simulated supply** that behaves realistically
so every downstream feature (reporting, attribution, recommendations, forecaster, learning phase) works.
Design it behind an interface so a real DSP can be plugged in later.

```python
class SupplyAdapter(Protocol):
    async def bid_opportunities(self, hour: datetime) -> AsyncIterator[Opportunity]: ...
    async def report_win(self, opp: Opportunity, bid: Bid) -> None: ...
class Opportunity: id, ts, household_id, channel_id, device_type, live_sport: bool, floor_cpm_micros
```

## Synthetic population (seeded by `make seed`, deterministic RNG seed 42)
- 200,000 sample households representing 120M US HH (scale factor 600). Distribution by state ∝ real state
  population shares (put shares in `seed/geo_states.json`), ZIPs sampled per state, timezone from state.
- Attributes: age_bucket (18-24 … 65+), gender of primary viewer, income bucket, education, family, homeowner,
  3–8 interests from the taxonomy (correlated: e.g. `sports > football` ↔ male 25-54 higher weight),
  devices (TV 100%, mobile 60%, tablet 25%, desktop 30%), daily viewing propensity 0.3–3.0 (lognormal).
- `ip_hash` = sha256 of a fake IP; the demo-store and pixel tests can "become" a household (dev toolbar).

## Opportunity generation (per simulated hour)
`n = Σ_hh propensity * viewing_curve[local_hour, weekday] * 1.2` ad slots; each slot picks a channel by the
household's channel affinity (category ↔ interests), device by device weights, `live_sport` if sports channel and
hour in 19–23. Floor CPM = channel.base_cpm × U(0.8,1.2).

## Bidder (per opportunity)
1. Candidate strategies = active strategies whose targeting matches the household (precompute per strategy a
   bitmap/set of eligible household ids at publish + nightly; check dayparting in HH local time; frequency cap via
   Redis counter `fc:{strategy}:{hh}:{day}`).
2. Pacing gate: `allowed_spend_so_far = daily_budget × cumulative_viewing_curve(now)`; skip if spent > allowed × 1.05.
3. Bid price:
   - manual: `min(max_cpm, ...)` fixed bid = max_cpm.
   - automatic: `bid = base_cpm_estimate × value_multiplier`, where
     `value_multiplier = clamp( p_conv(hh, channel, hour) / mean_p_conv , 0.6, 1.8)` once the strategy has ≥ 30
     conversions; during **learning** use exploration: ε-greedy (ε=0.3 days 1–7, 0.15 days 8–14, 0.05 after) over
     channel × daypart arms, Thompson sampling on conversion rate per arm (Beta priors).
   `p_conv` = logistic model per advertiser updated nightly (features: channel category, hour bucket, device,
   household in web audience, interest overlap with converters). Keep it simple: sklearn LogisticRegression.
4. Auction: highest bid ≥ floor wins; clearing price = max(floor, second bid) + 0.01 (second-price).
5. Win → insert `impressions` row, debit spend (transactions batch hourly), increment fc counter, choose creative
   by weight (random rotation; A/B split if creatives have equal weight and `ab_test=true`).

## Outcome simulation (so attribution has something to find)
For each impression, schedule a probable site visit/conversion event (written to `events` exactly as the pixel would):
```
base_visit_rate by goal: awareness 0.002, traffic 0.004, leads 0.004, sales 0.004, retargeting 0.012
multipliers: in_web_audience ×3, interest_match ×1.5, primetime ×1.2, creative_quality (hash of creative id → 0.8–1.3)
lag ~ exponential(mean 26h) truncated at 30d
visit → lead 6% (leads goal) / purchase 2.5% (sales), AOV lognormal(mean $85) per advertiser seed
app_promotion: install 0.15% of impressions, D7 revenue lognormal
organic baseline: households NOT exposed also generate visits at 60% of the exposed base rate (makes incrementality real)
holdout: 10% of eligible households per campaign are put in `holdout_households` and never bid on
```
These events go through the normal ingestion + attribution path (08) — the simulator must not write conversions directly.

## Status machine (`update_campaign_statuses` job)
draft → in_review (publish) → scheduled (start_date future) → learning (start, learning_until = start+14d) →
delivering → paused (user) → learning (resume, +5d) → completed (end_date passed or lifetime budget spent) ;
blocked if balance ≤ 0 or creative rejected or tracking broken > 72h for goals requiring it.

## Speed
`SIM_SPEED=60` → 1 real minute = 1 simulated hour. `make simulate HOURS=720` backfills 30 days fast
(batch mode without sleeping). Simulated clock stored in Redis `sim:now`; all "now" calls go through `clock.now()`.
