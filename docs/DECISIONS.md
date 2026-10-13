# Decisions — demo-readiness fix plan

Where the fix plan was silent, the simplest option was taken and recorded here
(`YYYY-MM-DD — decision — reason`). Earlier platform decisions: `ctv-platform-spec/docs/DECISIONS.md`.

2026-10-13 — `ENV` defaults to `production` — a deploy that forgets to set it must fail closed (dev routes and docs hidden); local `.env`, compose and tests set `development`.
2026-10-13 — API-key scopes are `read` (GET/HEAD/OPTIONS) and `write` (everything else); default `read`; an explicit empty list is rejected — least privilege. The "events" scope from task 14 is deferred: no API-key event-ingestion endpoint exists yet.
2026-10-13 — Keys stored with no scopes (created before enforcement) keep full access — they had it when issued; breaking existing integrations silently is worse.
2026-10-13 — Unbuilt settings screens are hidden by `NEXT_PUBLIC_SHOW_UNFINISHED` (off by default) and answer HTTP 404 via a `next.config` rewrite — `notFound()` inside the page rendered the 404 screen but with status 200 because the client settings layout had already streamed.
2026-10-13 — "No third-party brand names" applies to product copy, examples, prompts, comments and seed/fixture data. Kept: functional identifiers (the scraper's social/payment/app-store icon *skip* lists, the HTML term `apple-touch-icon`), required attributions (Pexels), and integration names in an integration context. Examples use reserved `.example` domains, since invented `.com` names may be real.
2026-10-13 — Studio's ownership rule: a URL must be the advertiser's website or a subdomain of it (exact label match; look-alike prefixes/suffixes refused). No website on file → generating from a URL is refused with a pointer to Settings → Advertisers; business-name-only generation (no site fetched) stays allowed. The free marketing generator (no advertiser, no login) is not gated — it has no ownership record to check against.
2026-10-13 — The retired `frontend/` folder (superseded by web/(marketing), no longer deployed) still contains the old example brand strings; deleting it is the owner's call.
