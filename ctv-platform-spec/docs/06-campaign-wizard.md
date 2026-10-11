# 06 — Campaign wizard, validation & live estimator

## Step 1 — CAMPAIGN ("Campaign details" + Draft pill)
Cards, top to bottom:
1. **Campaign Name** (text) + "Ask agent".
2. **Advertiser** — select (logo, name, industry · website) + "+" (create advertiser inline sheet) + kebab (edit).
3. **Campaign Type** — two groups of OptionCards:
   - PERFORMANCE GOALS: Awareness, Traffic, Leads, Sales
   - SPECIALIZED TYPES: Retargeting, App Promotion, ABM
   Right side of the card shows a contextual panel for the selected goal:
   - tracking chip if missing ("Pixel missing", "App Tracking missing")
   - one-line description (e.g. Sales: "Increase your sales."; App: "Drive app installs & in-app revenue.")
   - "Use cases" bullets (Sales: Increase web purchases, Drive revenue; App: Increase app installs, Drive in-app actions and revenue)
   - "Ad delivery: Optimize for {primary KPI}"
   - blocking InlineAlert if requirement missing, e.g. "Page View and Purchase events not set up yet — Sales campaigns
     require Page View and Purchase events on the advertiser's website." + button "Set up event" + "Why this setup matters?"
     (App: "App Promotion campaigns require App Tracking through your MMP." + "Manage App Tracking").
4. **Measurement** — "Choose how you'll measure this campaign success — Pick the metric you want to track and the
   result you're aiming for." Radio list of KPIs allowed for goal (00 table) with subtitle
   (e.g. "Cost per Purchase — Completed orders on your site", "ROAS — Revenue per dollar spent").
   Target input (currency, or ratio for ROAS) + link "Help me set my {KPI} target" (opens agent with benchmark answer
   from playbook `kpi_benchmarks`).
   "Show advanced options" → Attribution window: default from playbook (30-day, tag "Recommended"), "Edit window"
   → select 1h, 6h, 12h, 1d, 3d, 7d, 14d, 30d.
Footer: **Continue to Strategy ↓**.

Requirement table (from `playbook.yaml > goal_requirements`):
| goal | requires |
|---|---|
| traffic, retargeting | pixel with `page_view` seen in last 7 days |
| leads | + `lead` |
| sales | + `purchase` |
| app_promotion | app with status connected |
| abm | at least one company_list or firmographic audience selected in some strategy |
Missing requirement = **error** (blocks publish), not blocking the draft from saving.

## Step 2 — STRATEGY ("Strategy details")
Center cards:
1. **Strategy Name** + Ask agent. Default name auto-generated: `{placement} - {devices} - {location}` → "All Apps & Channels - TV - Entire US".
2. **Budget & Schedule** — Budget (currency) + select Daily Budget | Lifetime Budget; helper "Set a maximum amount of
   budget you are willing to spend per day."; Schedule start date (≥ today) + optional end date.
   Min daily budget $50 (lifetime: $50 × days). "Show more settings" reveals:
   - **Delivery Time Slots** — summary "Any time, Any day"; helper "Ads will be delivered in the respective timezone of
     the locations you targeted."; presets chips: Any time Any day, Custom, Primetime (Mon–Sun 19:00–23:00),
     After work (Mon–Fri 17:00–23:00), Work hours (Mon–Fri 09:00–17:00), Sleeping time (00:00–06:00), Weekend (Sat–Sun all),
     Work days (Mon–Fri all). DaypartGrid: rows Sunday..Saturday, columns 48 half-hour slots 12:00am..11:59pm; drag to paint; Reset.
   - **Frequency cap** — none | N impressions per household per day/week.
3. **Audience** — header copy: "We'll automatically reach people most likely to respond. You can adjust audience
   controls to reflect legal or practical constraints." Accordion rows:
   - **Locations** · summary ("Entire US") · "Controls enabled" — include/exclude list with geo autocomplete
     (state, DMA, city, ZIP, county, congressional district), bulk ZIP paste.
   - **In-Market & Interests** · "N segments selected" · toggle "Suggestions enabled" — "Suggest audiences from their
     points of interest". Search + SegmentTree (seed/interests.json) with reach badges + info tooltips.
   - **Demographics** — age, gender, household income, education, family/children, homeowner.
   - **Custom & Web Audiences** · "x included · y excluded" — source filter chips (All sources, API Upload, Company list,
     Contacts list, Customer.io, Firmographic, Fivetran, HubSpot, Klaviyo, Lookalike, Mailchimp, mParticle, Tealium,
     Twilio, Web Traffic) + "Add audience"; each audience row: name, type · size ("Web audience • 0 unique IPs"),
     segmented control Include | Exclude; lists "Included audiences" / "Excluded audiences"; Reset.
4. **Placement** — "We'll automatically show ads where people are most likely to respond. Choose specific placements if
   you have strict brand or legal requirements." Apps & Channels: radio **All Apps & Channels** ("Includes all current
   and future catalog inventory", total reach e.g. 1.1B) | **Select Apps & Channels** → ChannelPicker
   ("563 available", Select all, View selected only, category filter; tiles with name + reach). Devices: TV (default),
   Desktop, Mobile, Tablet. Option "Live sports only".
5. **Bidding** — OptionCards: **Automatic** "Automatically optimize bidding to get the best results out of your budget."
   | **Manual** "Manually define the fixed or maximum bid you are willing to pay for 1000 impressions (CPM)." + CPM input
   (min = max(channel floor) of selected channels; warning if below median floor).
6. **Creatives** — "Videos added here can be used in any strategy within this campaign. If you choose to select multiple
   videos, they will run at random for the length of the campaign." Selected list (thumb, name, "15s · date", Preview,
   remove). Buttons "Add a creative" (library picker / upload) and "Generate a creative" (Studio sheet, 12).
   Note "Your creative will remain private until campaign is published". Collapsible guidelines:
   Resolution 1920x1080, 16:9, .mp4, ≤ 500MB, 5–90s.
Footer: "↑ Back to campaign settings" + **Continue to Summary ↓**.

**Right: Strategy Estimate panel** (sticky, recomputed with 400ms debounce via POST /estimate):
Audience Size `lo - hi` · tabs Weekly | Daily · "Based on your daily budget of $X, your strategy estimated results are:"
Impressions `lo - hi`, Households `lo - hi` · Deliverability forecast pill (Insufficient=danger, Limited=warning,
Good=success, Excellent=success). If insufficient → danger card "Your targeting is too narrow. Broaden your audience to
improve delivery for your {Goal} campaign." + button "Adjust targeting" (scrolls to Audience card).

## Step 3 — SUMMARY
Read-only recap per section with "Edit" links, all validation issues listed (errors red, warnings amber),
total daily budget across strategies, account balance check ("Add funds" if balance < 3 days of budget),
checkbox to accept ad policies, **Publish campaign** button. Publish → status `in_review` → creative review job (12)
→ `scheduled` (start in future) or `learning`.

## Estimator algorithm (`services/estimator.py`) — deterministic, fast (<150ms)
```
universe = households (synthetic population, 07)
eligible = universe ∩ locations(include) − locations(exclude)
if interest_segment_ids: eligible ∩= any(interests)       # OR within interests
if demographics: AND across dimensions, OR within a dimension
if include_audiences: eligible ∩= union(members)          # retargeting/CRM narrows
eligible −= union(exclude_audiences)
placement_reach_share = sum(reach of selected channels)/total_reach  (1.0 if all)
device_share = TV 0.78, mobile 0.10, desktop 0.07, tablet 0.05 (sum selected)
daypart_share = selected half-hour slots weighted by viewing curve (playbook.viewing_curve)
audience_hh = |eligible| * placement_reach_share * device_share  (scale sample to national 120M HH)
supply_imps_week = audience_hh * avg_weekly_imps_per_hh(3.2) * daypart_share
expected_cpm = weighted channel base CPM * goal_multiplier (awareness 1.0, traffic 1.05, sales 1.1, retargeting 1.25)
                (manual: min(max_cpm, expected_cpm) and win-rate penalty if max_cpm < expected)
budget_imps_week = budget_daily*7 / expected_cpm * 1000
imps = min(supply_imps_week, budget_imps_week) ; households = imps / freq(≈2.4)
range = ±20%
deliverability: ratio = supply_imps / budget_imps → <0.5 insufficient, <1 limited, <3 good, else excellent
```
Return messages from playbook rules (e.g. retargeting audience < 1000 HH → "Your web audience is too small...").

## Validation codes (POST /campaigns/{id}/validate)
`MISSING_TRACKING, NO_STRATEGY, BUDGET_BELOW_MIN, END_BEFORE_START, NO_CREATIVE, CREATIVE_NOT_APPROVED,
TARGETING_INSUFFICIENT (warning), MANUAL_CPM_BELOW_FLOOR (warning), INSUFFICIENT_BALANCE, STRATEGY_DATES_OUTSIDE_CAMPAIGN,
RETARGETING_WITHOUT_WEB_AUDIENCE, ABM_WITHOUT_COMPANY_AUDIENCE, MIXED_WARM_COLD (warning, from playbook)`.
