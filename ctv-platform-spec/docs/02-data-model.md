# 02 — Data model (PostgreSQL)

Conventions: `id uuid pk default gen_random_uuid()`, `created_at/updated_at timestamptz`, money = `bigint` micros,
soft delete via `archived_at` where noted. Enums are Postgres enums (create via Alembic).

## Identity & accounts
```
users(id, email unique, password_hash, full_name, avatar_url, last_login_at)
accounts(id, name, timezone default 'America/New_York', currency 'USD', balance_micros bigint default 0,
         onboarding jsonb default '{}')          -- {"learned_ctv":bool,"pixel":bool,"stack":bool,"published":bool}
memberships(id, account_id, user_id, role enum('owner','admin','member','viewer'), unique(account_id,user_id))
invitations(id, account_id, email, role, token, expires_at, accepted_at)
api_keys(id, account_id, name, prefix, key_hash, scopes text[], last_used_at, revoked_at)
oauth_apps(id, account_id, name, client_id, client_secret_hash, redirect_uris text[])   -- "My applications"
```

## Advertisers & tracking
```
advertisers(id, account_id, name, website_url, industry enum(see below), logo_url, timezone, archived_at)
  industry: 'apps_gaming','ecommerce','education_nonprofit','automotive','media_entertainment','legal',
            'politics','home_improvement','retail','b2b','finance','health_wellness','travel','food_bev','other'
pixels(id, account_id, advertiser_id unique, public_key text unique, install_method enum('gtm','shopify','manual',
       's2s','wordpress','wix','squarespace','woocommerce','bigcommerce','ticketmaster','eventbrite'),
       status enum('not_installed','active','stale'), last_event_at)
pixel_event_types(id, pixel_id, event enum('page_view','lead','add_to_cart','purchase','signup','custom'),
       custom_name, enabled bool, last_seen_at)
apps(id, account_id, advertiser_id, platform enum('ios','android'), store_url, bundle_id,
     mmp enum('appsflyer','adjust','branch','kochava','singular','airbridge','gamesight'), mmp_app_id,
     status enum('pending','connected','error'), last_postback_at)
```

## Audiences
```
audiences(id, account_id, advertiser_id, name,
  source enum('contacts_list','company_list','firmographic','web_traffic','lookalike','api_upload',
              'klaviyo','hubspot','mailchimp','customerio','mparticle','tealium','twilio','fivetran'),
  status enum('processing','counting','ready','no_data','error'),
  definition jsonb,          -- per-source, see below
  uploaded_records int, matched_households int, match_rate numeric(5,4), last_synced_at, archived_at)
audience_members(audience_id, household_id, primary key(audience_id, household_id))
```
`definition` examples:
- web_traffic: `{"pixel_id":..., "rules":[{"url_contains":"/checkout"}], "events":["page_view"], "lookback_days":30}`
  Seeds 3 default web audiences per pixel: **Visitors** (any page_view, 30d), **Leads** (lead event), **Purchasers** (purchase event).
- firmographic: `{"industries":["software"],"company_size":["51-200"],"job_functions":["engineering"],"seniority":["manager"]}`
- lookalike: `{"seed_audience_id":..., "size_pct": 5}`  (1–10% of national HH)
- contacts_list / company_list: `{"file_key":"s3://...","columns":{"email":"Email","zip":"Zip"}}`

## Inventory & taxonomy (seeded, global — no account_id)
```
households(id, ip_hash, zip, dma_code, state, city, county, congressional_district, timezone,
           age_bucket, gender, income_bucket, education, family, homeowner bool, ethnicity_affinity null,
           interests text[], device_types text[])          -- synthetic population, see 07
channels(id, name, category enum('entertainment','news','sports','kids','movies','lifestyle','music','spanish','fast'),
         publisher, reach_households bigint, base_cpm_micros bigint, is_premium bool, logo_url)
interest_segments(id, parent_id, name, reach_households bigint)    -- tree, see seed/interests.json
geos(id, type enum('country','state','dma','city','zip','county','congressional_district'), code, name, parent_id, households bigint)
companies(id, domain, name, industry, size_bucket)                 -- for ABM/firmographic
company_households(company_id, household_id)
```

## Campaigns
```
campaigns(id, account_id, advertiser_id, name,
  goal enum('awareness','traffic','leads','sales','retargeting','app_promotion','abm'),
  kpi enum('cpm','cost_per_household','cps','cpv','cpl','cpp','roas','cpi','cost_per_account'),
  kpi_target_micros bigint null, kpi_target_ratio numeric null,     -- ROAS uses ratio
  attribution_window_hours int default 720,                          -- 1..720
  app_id null, pixel_id null,
  status enum('draft','in_review','scheduled','learning','delivering','paused','blocked','completed','archived'),
  blocked_reason text null, published_at, learning_until timestamptz null)
strategies(id, campaign_id, account_id, name,
  budget_type enum('daily','lifetime'), budget_micros bigint, start_date date, end_date date null,
  dayparting jsonb,     -- {"preset":"any"|"primetime"|"after_work"|"work_hours"|"sleeping"|"weekend"|"work_days"|"custom",
                        --  "grid": {"mon":[0..47 slot indexes], ...}}  30-min slots, location timezone
  frequency_cap jsonb,  -- {"impressions":3,"per":"day"} null = none
  locations jsonb,      -- {"include":[{"type":"state","code":"CA"}], "exclude":[...]}  empty include = Entire US
  interest_segment_ids uuid[], suggestions_enabled bool default true,
  demographics jsonb,   -- {"age":["25-34"],"gender":["f"],"income":[...],"education":[...],"family":[...]}
  include_audience_ids uuid[], exclude_audience_ids uuid[],
  placement_mode enum('all','selected'), channel_ids uuid[], device_types text[] default '{tv}',
  live_sports_only bool default false,
  bidding_mode enum('automatic','manual'), max_cpm_micros bigint null,
  status enum('draft','active','paused','completed'), position int)
strategy_creatives(strategy_id, creative_id, weight int default 1)
```

## Creatives
```
creatives(id, account_id, advertiser_id, name, source enum('upload','studio','canva'),
  file_key, transcoded_key, thumbnail_key, duration_ms, width, height, size_bytes,
  review_status enum('pending','processing','approved','rejected','needs_changes'), review_notes text,
  labels text[], archived_at)
studio_jobs(id, account_id, advertiser_id, input jsonb, status, script jsonb, output_creative_id, error)
```

## Delivery & measurement
```
impressions(id bigserial, ts timestamptz, account_id, campaign_id, strategy_id, creative_id, channel_id,
            household_id, device_type, cost_micros bigint, live_sport bool)        -- partition by month
events(id bigserial, ts, account_id, advertiser_id, source enum('pixel','mmp','s2s'),
       event text, household_id null, ip_hash, revenue_micros bigint, order_id, url, user_agent, raw jsonb)
conversions(id bigserial, event_id, impression_id, campaign_id, strategy_id, creative_id, channel_id,
            ts, event text, revenue_micros, lag_seconds int, model enum('last_touch'))
holdout_households(campaign_id, household_id)    -- control group for incrementality (07/11)
```
Rollups (written by `rollups.py`, used by every report):
```
stats_hourly(ts_hour, account_id, advertiser_id, campaign_id, strategy_id, creative_id, channel_id, state, dma,
             impressions, households_reached, spend_micros, sessions, leads, purchases, installs, revenue_micros)
stats_daily(...same keys with date..., + zip, age_bucket, gender, interest_segment_id nullable)
```

## Intelligence
```
recommendations(id, account_id, campaign_id, strategy_id null,
  type enum('increase_budget','expand_audience','switch_to_auto_bidding','broaden_placement',
            'fix_tracking','add_creative','split_retargeting_prospecting','extend_attribution_window'),
  title, body, projected jsonb,   -- {"metric":"sessions","current":120,"projected":168,"uplift_pct":40}
  action jsonb,                   -- machine-applicable patch: {"op":"update_strategy","id":..,"patch":{"budget_micros":..}}
  status enum('open','applied','rejected','expired'), reject_reason text, reject_note text,
  created_at, expires_at)         -- +90 days
recommendation_suppressions(account_id, campaign_id null, type, until timestamptz null)   -- null campaign = account-wide
elasticities(advertiser_id, goal, alpha numeric, beta numeric, r2 numeric, n_days int, updated_at)
agent_threads(id, account_id, user_id, context jsonb, created_at)
agent_messages(id, thread_id, role, content jsonb, created_at)
agent_proposals(id, thread_id, action jsonb, status enum('proposed','applied','discarded'))
```

## Billing
```
transactions(id, account_id, type enum('topup','spend','refund','coupon','referral_credit'),
             amount_micros bigint (signed), balance_after_micros, ref jsonb, created_at)
payment_methods(id, account_id, provider, provider_ref, brand, last4, exp_month, exp_year, is_default)
invoices(id, account_id, period_start, period_end, amount_micros, status, pdf_key)
coupons(id, code unique, amount_micros, expires_at, max_redemptions) ; coupon_redemptions(coupon_id, account_id, at)
report_definitions(id, account_id, name, dimensions text[], metrics text[], filters jsonb, date_range jsonb,
                   schedule jsonb null, recipients text[])
notifications(id, account_id, user_id null, kind, title, body, link, read_at)
```

## Indexes (minimum)
`impressions(campaign_id, ts)`, `impressions(household_id, ts)`, `events(advertiser_id, household_id, ts)`,
`stats_daily(account_id, date)`, `stats_daily(campaign_id, date)`, GIN on `households(interests)`.
