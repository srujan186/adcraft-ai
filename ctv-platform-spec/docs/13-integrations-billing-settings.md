# 13 — Settings, integrations, billing, developers

Settings layout: left nav (240px) with group headings, content right. Page header per sub-page.

## Account
- **General**: account name, timezone, currency (USD only), logo; danger zone (close account).
- **Members**: table (name, email, role, status, last active), "Invite member" (email + role), change role, remove.
  Roles: owner (all), admin (all except billing ownership transfer), member (campaigns/audiences/creatives), viewer (read).
- **Advertisers**: header "Advertisers — Manage your brand or clients by listing them as separate Advertisers within your
  account." CTA "+ New advertiser". Rows: logo, name, industry · website, "Edit advertiser". Form: name, website, industry,
  logo upload, timezone.

## Integrations
- **Marketplace**: cards grid with category filter (Measurement & Attribution, CRM & CDP, E-commerce & Site builders,
  Data & Reporting, Creative, AI agents). Each card: logo placeholder (generic icon — don't use real logos unless you
  have rights), name, one-liner, "Connect".
- Implement real connectors for: **Shopify** (pixel install via instructions), **Google Tag Manager** (instructions),
  **Klaviyo / HubSpot / Mailchimp** (API key → list lists → import segment as audience; nightly re-sync),
  **CSV/API upload**. Everything else = "Coming soon" card that records interest.
- **Installed integrations**: list with status, last sync, "Sync now", "Disconnect".

## Tracking
Web Pixel and App Tracking (see 08).

## Billing (prepaid balance)
- **Balance & transactions**: balance KPI, "Add funds" (amount presets $250/$500/$1,000/custom, payment method),
  auto-recharge toggle (threshold + amount), transactions table (date, type, amount, balance after). Spend is
  debited hourly by the simulator as one aggregated `spend` transaction per campaign per hour.
- **Payment methods**: list cards (brand, •••• last4, exp, default), "Add credit card" → FakePaymentProvider form in dev
  (accepts test number 4242…, never store full PAN — store only brand/last4/exp/token). Stripe adapter optional.
- **Invoices** (monthly, generated PDF via WeasyPrint), **Receipts** (per top-up), **Coupons** (redeem code → credit),
  **Refer & earn** (referral link; credit both accounts when referee spends $X).
- Campaign blocking when balance ≤ 0 (07); banner across app "Your balance is empty — campaigns are paused".

## Developers
- **API keys**: create (name, scopes: read, write, events), shown once, revoke. Prefix `lum_`.
- **My applications**: OAuth client registration for partners (client id/secret, redirect URIs). Implement
  authorization-code flow later; v1 just stores them.
- Public API = same endpoints as 03 with API-key auth; OpenAPI docs at `/api/docs`.
- Optional **MCP server** (`/mcp`) exposing the agent's read tools + propose_change so external AI agents can plan
  and optimize campaigns.
