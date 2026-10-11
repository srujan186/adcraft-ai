# 03 — REST API (FastAPI, prefix `/api/v1`)

Auth: `Authorization: Bearer <jwt>` + `X-Account-Id`, or `Authorization: Bearer lum_<api_key>` (account inferred).
Errors: `{"error":{"code":"string","message":"string","fields":{...}}}`. Lists: `?page=&page_size=&sort=&q=` →
`{"items":[...],"total":n}`. Money fields end in `_micros`.

## Auth & account
| Method | Path | Notes |
|---|---|---|
| POST | /auth/signup | {email,password,full_name,company} → creates user+account+owner membership |
| POST | /auth/login, /auth/refresh, /auth/logout | |
| GET | /me | user + memberships + active account + onboarding flags |
| PATCH | /accounts/{id} | name, timezone |
| GET/POST/DELETE | /members, /members/invite, /members/{id} | |
| GET/POST/DELETE | /api-keys | returns full key once on create |
| GET/POST/DELETE | /oauth-apps | |

## Advertisers & tracking
| GET/POST/PATCH/DELETE | /advertisers[/{id}] | |
| POST | /advertisers/{id}/pixel | {install_method} → pixel with snippet |
| GET | /pixels/{id}/status | events seen in last 24h per type |
| POST | /pixels/{id}/test-event | fire synthetic page_view |
| GET/POST/PATCH | /apps[/{id}] | MMP connection; returns postback URL `/mmp/{mmp}/{app_id}` |
| GET (public) | /px.js | pixel script |
| POST (public) | /e | pixel event ingest (see 08) |
| POST (public) | /mmp/{mmp}/{app_id} | MMP postback ingest |
| POST | /s2s/events | server-to-server events (API key auth) |

## Inventory & taxonomy
| GET | /channels?category=&q= | with reach + "All Apps & Channels" total |
| GET | /interest-segments | tree with reach |
| GET | /geos/search?q=&type= | autocomplete for location include/exclude |
| GET | /companies/search?q= | ABM |

## Audiences
| GET/POST/PATCH/DELETE | /audiences[/{id}] | POST multipart for list uploads |
| POST | /audiences/lookalike | {seed_audience_id, size_pct} |
| POST | /audiences/{id}/refresh | re-match / re-sync |

## Campaigns & strategies
| GET | /campaigns?status=&goal=&advertiser_id=&from=&to= | includes rolled-up metrics for range |
| POST | /campaigns | creates draft + one default strategy "All Apps & Channels - TV - Entire US" |
| GET/PATCH/DELETE | /campaigns/{id} | |
| POST | /campaigns/{id}/validate | returns `{ok, issues:[{level:'error'|'warning', step, field, code, message}]}` |
| POST | /campaigns/{id}/publish | validate → status in_review → creative review → scheduled/learning |
| POST | /campaigns/{id}/pause, /resume, /duplicate, /archive | resume sets learning_until = now+5d |
| GET/POST | /campaigns/{id}/strategies | |
| GET/PATCH/DELETE | /strategies/{id} | |
| POST | /strategies/{id}/duplicate | |
| POST | /estimate | body = strategy draft + campaign goal → `{audience_households:[lo,hi], weekly:{impressions:[lo,hi],households:[lo,hi]}, daily:{...}, deliverability:'insufficient'|'limited'|'good'|'excellent', messages:[...]}` (06) |
| GET | /strategies/{id}/forecast | budget→outcome curve (09) |

## Creatives & studio
| GET/POST/PATCH/DELETE | /creatives[/{id}] | POST = presigned upload flow: `POST /creatives/upload-url` → PUT to S3 → `POST /creatives {file_key,name}` |
| POST | /studio/jobs | {advertiser_id, url? , gmaps_name?, duration_s:15|30, voice, tone} |
| GET | /studio/jobs/{id} | poll status, returns creative when done |

## Reporting & insights
| GET | /stats/timeseries?metric=&granularity=day&from=&to=&campaign_id= | dashboard + campaigns chart |
| GET | /stats/table?level=campaign|strategy|creative&from=&to= | campaigns list tabs |
| POST | /reports/run | {dimensions[], metrics[], filters, date_range} → rows |
| GET/POST/PATCH/DELETE | /reports[/{id}] | saved definitions + schedule |
| GET | /reports/{id}/download?format=csv | |
| GET | /insights/overview?advertiser_id=&from=&to= | geo, time-of-day×weekday, demographics, inventory, interests, creative |
| GET | /insights/incrementality?advertiser_id= | eligibility + lift results |

## Intelligence
| GET | /recommendations?status=open | grouped by type if > 3 |
| POST | /recommendations/{id}/apply | executes `action` patch, returns updated entity |
| POST | /recommendations/{id}/reject | {reason_code, note?} |
| POST | /agent/threads | {context:{page, campaign_id?, strategy_id?, section?}} |
| POST | /agent/threads/{id}/messages | SSE stream: tokens, tool_calls, proposals |
| POST | /agent/proposals/{id}/apply , /discard | |
| GET | /agent/suggested-questions?section= | static per section (10) |

## Billing & misc
| GET | /billing/balance, /billing/transactions | |
| POST | /billing/topup | {amount_micros, payment_method_id} (FakePaymentProvider) |
| GET/POST/DELETE | /billing/payment-methods | |
| GET | /billing/invoices, /billing/receipts | |
| POST | /billing/coupons/redeem | |
| GET | /notifications ; POST /notifications/{id}/read | |
| GET | /integrations/marketplace ; GET/POST/DELETE /integrations/installed | |
