# 04 — Frontend spec (every route & screen)

All app routes live under `/dashboard`. Top nav items (in order): **Dashboard · Campaigns · Audiences · Library ·
Reports · Insights [New badge]**, then right side: bell, **Ask Agent**, account switcher.
Account switcher menu: account name, Settings, Advertisers, Billing, Help center, Log out.

---------------------------------------------------------------------------------------------------
## /dashboard — Home
Header: "Dashboard" + subtitle "Welcome to Lumen! Finish the steps below to get your first streaming campaign live."
CTA: **+ Create campaign**.

Grid (12 cols, gap 24): left 8 cols, right 4 cols.

**Left column**
1. **Get started card** (hidden when all done): title "Get started with Lumen!", progress text
   "You're N% closer to delivering best-in-class campaigns" + progress bar. 4 checklist rows (icon, title, sub, chevron):
   - Discover CTV advertising — "Learn how streaming ads work" → opens explainer dialog (3 slides)
   - Connect your pixel — "See the visits and sales your ads drive" → /dashboard/settings/tracking/web
   - Connect your stack — "Integrate your marketing tools and data sources" → /dashboard/settings/integrations-marketplace
   - Publish your first campaign — "Start to reach your audience" → wizard
   Each completed row shows a green check. Progress = completed/4.
2. **Explainer banner** "Get your business on TV today": one paragraph ("Your video runs between shows on 500+ apps,
   shown only to people in the places and interests you pick. Nobody clicks a TV ad, so results show up as visits and
   sales on your site over the following days.") + buttons "Explain CTV advertising" (opens Ask Agent with that
   question) and "Skip, I'm familiar with this" (sets onboarding.learned_ctv).
3. **FAQ row**: 3 small cards (Billing / Measurement / Tracking) each with a question + "Get the answer →" (opens agent).
4. **Last 7 days trends** card: metric tabs (Spend, Impressions, Households, Sessions, Conversions, ROAS); line chart.
   Empty: box icon, "No campaign delivering yet", "Create a first campaign to get started".
5. **Performance forecaster** card: shows ForecastChart for the strategy with the biggest projected gain (09) or an
   empty state "Forecaster appears once a published campaign has enough delivery history" + "Read article".
6. **Recommendations** card: list of RecommendationCards (09), or "You're all caught up — New performance
   recommendations appear as the agent finds them".

**Right column**
1. **Need help?** card with a friendly illustration, "Ask the agent for an instant answer, or book a call with an expert",
   buttons "Ask Agent" + "Book a call" (link to settings-configured URL).
2. **Campaigns** status card: rows Delivering / Paused / Blocked / Draft each with a count chip + arrow → /dashboard/campaigns?status=x.
3. **Feed**: list of help-article links with "1 min read" (static markdown in `/web/content/help/*.md`, rendered at /help/[slug]).

---------------------------------------------------------------------------------------------------
## /dashboard/campaigns — Campaigns list (route name `reporting` in the reference; use `campaigns`)
Header "Campaigns", subtitle "See how your campaigns perform.", CTA "+ Create campaign".
Filter bar: search, FilterPills **Advertiser**, **Campaign status**, **Goal**, DateRangePicker (default last 7 days),
toggle group [line chart | bar chart | hide chart], kebab (export CSV).
Chart area: ChartCard with two selectable metrics (left/right axis). Empty: "No data available for the selected dates".
Tabs: **Campaigns | Strategies | Creatives** (+ right: "Edit columns", "Download report").
Table columns (Campaigns tab, user can toggle): checkbox, Campaign name (+ "Edit" link under name), Status,
Performance (KPI actual vs target, colored), Goal, Performance objective (e.g. "$100 Cost per Install"),
Budget, Spend, Impressions, Households, CPM, Sessions, Conversions, CPA, Revenue, ROAS, Start, End.
Footer row: "Total of N campaigns" with summed metrics. Row actions (kebab): Edit, Duplicate, Pause/Resume, Archive.
Strategies/Creatives tabs: same metrics at that level, with parent campaign column.
Bulk actions when rows checked: Pause, Resume, Archive.

## /dashboard/campaigns/new → creates draft via POST /campaigns then redirects to edit
## /dashboard/campaigns/[id]/edit — Campaign wizard (full spec in 06)
Top bar (white, not navy): "< Back" left; center "You are creating... / {campaign name}"; right "Help center" link,
"Save" (outline, disabled until dirty), "Ask Agent".
Left StepRail: 01 CAMPAIGN "Set your campaign"; 02 STRATEGY "Set your strategies" (expandable list of strategies,
each with status dot and kebab: rename, duplicate, delete) + "Add strategy +"; 03 SUMMARY "Review your campaign".
## /dashboard/campaigns/[id] — Campaign detail (published)
Header with name, StatusPill, goal badge, actions (Edit, Pause/Resume, Duplicate). Learning banner if learning
("Learning — results are not representative until {date}"). KPI tiles row. ChartCard. Strategies table.
Recommendations for this campaign. Forecaster for selected strategy.

---------------------------------------------------------------------------------------------------
## /dashboard/audiences
Header "Audiences", subtitle "Create and save audiences to reach the people who matter to your business.",
CTA "+ New audience" (dropdown: **Custom audience**, **Lookalike audience**).
Filters: search, Source, Advertiser, Status. Table: Name (+Manage), Source, Advertiser, Status pill
(Processing / Counting members / Ready / No data / Error), Match rate, Matched audience, Active strategies, Last updated.
**New custom audience sheet** (3-step, dots): Step 1 "Select audience source" — searchable list of OptionCards:
Contacts list ("Upload a list of people you want to reach in your campaigns"), Firmographic audience ("Build an
audience using company and employee attributes"), Company list ("Upload a list of companies..."), Web Traffic ("Target
the right users ... based on URL they visited", shows "Pixel missing" chip if no pixel), Klaviyo, HubSpot, Mailchimp,
Customer.io, mParticle, Tealium, Twilio, Fivetran ("Connect with your X account and reach your existing customers").
Step 2 source-specific config (CSV dropzone + column mapping; firmographic filters; URL rules; integration list picker).
Step 3 name + advertiser + review → Create.
**Lookalike sheet**: seed audience select, size slider 1–10% with estimated households, name.

## /dashboard/library
Header "Library", subtitle "Import and manage your creatives.", buttons "Open Studio" (outline) + "Upload" (primary).
Filters: Advertiser. Left mini-nav: All Creatives (n), Unlabeled (n), labels..., "+ Add label".
Table: thumbnail, Creative name, Label, Duration, Review status, Date added, Last updated, actions (Preview, Edit,
More: rename, label, download, archive). Pagination "Showing 1 to n of N", rows per page.
## /dashboard/library/studio — see 12.

---------------------------------------------------------------------------------------------------
## /dashboard/reports — Report builder (see 11)
Top: editable report name "My report", subtitle "Create a report to analyze your data.", buttons Save, Filters,
DateRange, Download, Schedule, **Run**. Left panel: Dimensions (grouped, checkboxes) and Metrics (grouped).
Main: results table; empty "Nothing to display yet — Select metrics and dimensions to start then click on Run".
Saved reports list at /dashboard/reports/saved.

## /dashboard/insights/overview and /dashboard/insights/incrementality
Header "Insights", subtitle "Campaign performance and incremental impact across your account". Tabs Overview |
Incrementality. Advertiser select + date range. Overview cards: Geographic heatmap (US states, metric selector),
Time performance (weekday × hour heatmap), Demographics (age/gender bars), Inventory (top channels table),
In-market & interests (top segments), Creative (per-creative metrics). Bottom "Need help? Book a call".
Incrementality: if not eligible → empty state "Incrementality is coming soon / unlocks automatically once an
advertiser meets the eligibility thresholds" + progress to thresholds; else lift results (see 11).

---------------------------------------------------------------------------------------------------
## /dashboard/settings/* — left settings nav (see 13)
Groups: **Account**: General, Members, Advertisers · **Integrations**: Marketplace, Installed integrations ·
**Tracking**: Web Pixel, App Tracking · **Billing**: Balance & transactions, Payment methods, Invoices, Receipts,
Coupons, Refer & earn · **Developers**: My applications, API keys.

## Global
- **Ask Agent side panel** (Sheet from right, 420px): thread, suggested questions, input, "Open chat" full view.
- **AgentPopover** (anchored to section "Ask agent" button): input "What's on your mind?" + 2 suggested questions
  for that section; answer renders in a floating card (bottom-right of section) with "Dismiss" / "Open chat".
  While the agent runs: wizard form is disabled with note "While the agent is running you cannot edit any campaign settings."
- **Notifications** dropdown from bell.
- **/demo-store** — 3-page fake shop (home, product, checkout→thank-you) with the pixel installed and a
  "Simulate visitor from household" dev toolbar, used to test tracking end-to-end.
