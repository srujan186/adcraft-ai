import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "API reference — AdCraft AI",
  description:
    "Generate video ads programmatically over plain JSON HTTP. Endpoints for scripts, full renders, scraping and file download.",
};

// Written against the actual route handlers in backend/routers/. If an endpoint
// changes, update this page with it.

type Endpoint = {
  method: "GET" | "POST";
  path: string;
  summary: string;
  body?: string;
  response: string;
  note?: string;
};

const ENDPOINTS: Endpoint[] = [
  {
    method: "POST",
    path: "/api/generate/video",
    summary:
      "The full pipeline. Scrapes the URL, writes a script, synthesises narration, mixes music and renders an MP4. This is what the web app calls.",
    body: `{
  "url": "stripe.com",
  "ad_style": "modern",
  "duration": 15
}`,
    response: `{
  "success": true,
  "data": {
    "video_url": "/api/output/a1b2c3d4_ad.mp4",
    "render_id": "a1b2c3d4",
    "script": { "headline": "...", "voiceover": "...", ... },
    "scraped": { "business_name": "...", "colors": { ... }, ... }
  }
}`,
    note: "Long-running — expect this to take most of a minute. ad_style is one of modern, bold, minimal or playful; duration is 15 or 30.",
  },
  {
    method: "POST",
    path: "/api/generate/from-url",
    summary:
      "Scrape and write a script, but stop before rendering. Useful for reviewing or storing copy without paying the cost of a render.",
    body: `{
  "url": "stripe.com",
  "ad_style": "bold",
  "duration": 30
}`,
    response: `{
  "success": true,
  "data": {
    "scraped":  { "business_name": "...", "tagline": "...", ... },
    "script":   { "headline": "...", "cta": "...", ... },
    "metadata": { "url": "...", "ad_style": "bold", "duration": 30 }
  }
}`,
  },
  {
    method: "POST",
    path: "/api/generate/script",
    summary:
      "Write a script from brand details you already hold, skipping the scrape entirely.",
    body: `{
  "business_name": "Acme Coffee",
  "description":   "Speciality coffee roasted in Leeds.",
  "tagline":       "Roasted properly.",
  "ad_style":      "playful",
  "duration":      15
}`,
    response: `{
  "success": true,
  "data": {
    "script": {
      "headline": "...", "subtext": "...", "cta": "...",
      "voiceover": "...", "music_style": "...",
      "scene_description": "...", "color_mood": "...",
      "key_message": "..."
    },
    "metadata": { "business_name": "...", "model_used": "..." }
  }
}`,
    note: "business_name and description are required. Returns 400 if either is blank, or if ad_style / duration are outside the allowed values.",
  },
  {
    method: "POST",
    path: "/api/scrape",
    summary: "Extract branding from a URL without generating anything.",
    body: `{ "url": "stripe.com" }`,
    response: `{
  "business_name": "Stripe",
  "description":   "...",
  "tagline":       "...",
  "logo_url":      "https://...",
  "colors": { "primary": "#635bff", "secondary": "#ffffff", "accent": "#0a2540" },
  "features": [],
  "domain": "stripe.com",
  "scrape_failed": false
}`,
    note: "If the site blocks scraping, scrape_failed is true and scrape_message explains why — the request still returns 200 with fallback data.",
  },
  {
    method: "GET",
    path: "/api/output/{filename}",
    summary: "Download a rendered video by filename, as returned in video_url.",
    response: `Content-Type: video/mp4

<binary>`,
    note: "Returns 404 if the render id does not exist.",
  },
  {
    method: "GET",
    path: "/api/health",
    summary: "Liveness check.",
    response: `{ "status": "ok", "message": "AdCraft AI is running" }`,
  },
];

function MethodPill({ method }: { method: "GET" | "POST" }) {
  return <span className={`api-method api-${method.toLowerCase()}`}>{method}</span>;
}

export default function ApiPage() {
  return (
    <>
      <section className="page-hero">
        <div className="container container-narrow">
          <span className="eyebrow">Developers</span>
          <h1 className="h1" style={{ fontSize: "clamp(2rem, 4.4vw, 3.4rem)" }}>
            API reference
          </h1>
          <p className="lead" style={{ marginTop: "1rem" }}>
            The web app is just a client. Every endpoint it uses is plain JSON over
            HTTP — no SDK, no auth during the beta.
          </p>

          <div className="card" style={{ marginTop: "2rem", background: "var(--surface2)" }}>
            <p className="mega-col-title" style={{ marginBottom: "0.6rem" }}>Base URL</p>
            <pre className="code-block"><code>http://localhost:8000</code></pre>
            <p className="hint" style={{ marginTop: "0.75rem" }}>
              Set <code className="code-inline">NEXT_PUBLIC_API_URL</code> in the frontend
              environment to point at a deployed backend instead.
            </p>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container container-narrow">
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            {ENDPOINTS.map((ep) => (
              <div className="card" key={ep.path + ep.method}>
                <div className="api-head">
                  <MethodPill method={ep.method} />
                  <code className="api-path">{ep.path}</code>
                </div>
                <p className="feature-desc" style={{ margin: "0.85rem 0 1rem" }}>
                  {ep.summary}
                </p>

                {ep.body && (
                  <>
                    <p className="api-label">Request body</p>
                    <pre className="code-block"><code>{ep.body}</code></pre>
                  </>
                )}

                <p className="api-label">Response</p>
                <pre className="code-block"><code>{ep.response}</code></pre>

                {ep.note && (
                  <p className="hint" style={{ marginTop: "0.85rem" }}>{ep.note}</p>
                )}
              </div>
            ))}
          </div>

          <div className="note-box" style={{ marginTop: "2rem" }}>
            <span>⚠️</span>
            <span>
              There is no authentication during the beta. Do not expose a deployed
              backend publicly without putting auth and rate limiting in front of it —
              every render costs CPU time.
            </span>
          </div>

          <div style={{ marginTop: "2rem", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
            <Link href="/resources/help" className="btn btn-secondary">Help centre</Link>
            <Link href="/resources/changelog" className="btn btn-secondary">Changelog</Link>
          </div>
        </div>
      </section>
    </>
  );
}
