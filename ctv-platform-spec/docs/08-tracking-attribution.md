# 08 — Tracking & attribution

## Pixel setup UI (Settings › Tracking › Web Pixel)
Empty state: "No web tracker set up yet — You don't have any advertiser setup with a web tracker" + **Set up a pixel**.
Sheet wizard (5 dots):
1. Install method (OptionCards with logos): Google Tag Manager, Shopify, Manual (JavaScript), Server-to-Server,
   Ticketmaster, Eventbrite, WordPress, Wix, Squarespace, WooCommerce, BigCommerce.
2. Select the advertiser to install your pixel (searchable radio list).
3. Install instructions for the method (snippet with copy button; GTM: custom HTML tag steps; Shopify: paste pixel
   ID into Customer Events; S2S: endpoint + API key + curl example).
4. Events: toggle Page View (always on), Lead, Add to cart, Purchase (with value & currency), Sign up, Custom; shows
   code example `lumen('track','purchase',{value:49.9,currency:'USD',order_id:'123'})`.
5. Verify: "Waiting for events..." live poll of /pixels/{id}/status, green check per event type when seen,
   "Send test event" button.
List view afterwards: per advertiser pixel row: method, status (Active / Not installed / Stale >7d), last event, events table.

## pixel.js (`/pixel`, < 3KB gz)
```html
<script>!function(w,d,k){w.lumen=w.lumen||function(){(w.lumen.q=w.lumen.q||[]).push(arguments)};
var s=d.createElement('script');s.async=1;s.src='{API}/px.js';d.head.appendChild(s);w.lumen('init',k);
w.lumen('track','page_view');}(window,document,'PIXEL_PUBLIC_KEY');</script>
```
- Sends `navigator.sendBeacon` POST `/e` JSON `{k, ev, url, ref, ts, value?, currency?, order_id?, custom?}`.
- First-party cookie `_lm_id` (random uuid, 1 year) for de-dup; no PII collected.
- SPA support: listen to `history.pushState`/`popstate` → page_view.

## Ingest `/e`
- Look up pixel by public key → advertiser. Resolve household: `ip_hash = sha256(client_ip + PEPPER)`,
  join `households.ip_hash` (in simulation the demo store sends header `X-Sim-Household` in dev only).
- Dedupe: same `(_lm_id, ev, order_id)` within 24h. Bot filter: UA regex list.
- Insert `events`, update `pixel_event_types.last_seen_at`, enqueue `attribute_event(event_id)`.
- Respond 204 within 20ms (do heavy work async).

## MMP postbacks `/mmp/{mmp}/{app_id}`
Normalize to `events(source='mmp', event in install|purchase|custom, revenue)`. Each MMP has a small mapper.
App Tracking settings page: list apps, "+ Add app" (platform, store URL, MMP select) → shows postback URL + steps.

## Attribution engine (`services/attribution.py`)
For each event with a household:
```
window = campaign.attribution_window_hours (use the longest among the advertiser's campaigns to fetch candidates)
candidates = impressions WHERE household_id = e.household_id AND advertiser = e.advertiser
                         AND ts BETWEEN e.ts - window AND e.ts
filter per-campaign window; pick LAST impression (last-touch view-through)
if found → insert conversions(event_id, impression_id, campaign, strategy, creative, channel, lag_seconds, revenue)
```
- Session = page_view events from same `_lm_id` within 30 min collapse into 1 session; only the session start is
  attributed as "session".
- Metrics definitions (use everywhere): sessions, leads, purchases, installs, revenue = sum attributed revenue,
  ROAS = revenue / spend, CPS/CPL/CPP/CPI = spend / count, CPM = spend/impr×1000, households = distinct HH reached.
- Reattribution: if an impression arrives late (it can't in simulation) ignore.
- Third-party partner exports (optional later): nightly CSV of impressions per HH to S3 for MMM/incrementality tools.
