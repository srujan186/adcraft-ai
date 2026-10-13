import type { NextConfig } from "next";

import { UNFINISHED_ROUTES } from "./src/lib/unfinished-routes";

// The free Creative Studio on the marketing site (app/(marketing)) talks to the video
// generator in backend/ through same-origin /api/* paths. Proxy those to it; the
// platform API (/api/v1/*) is called absolutely via NEXT_PUBLIC_API_URL, never here.
const VIDEO_APP_ORIGIN = process.env.VIDEO_APP_ORIGIN ?? "http://127.0.0.1:8001";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Env surfaced to the browser (product name is configurable per CLAUDE.md).
  env: {
    NEXT_PUBLIC_PRODUCT_NAME: process.env.NEXT_PUBLIC_PRODUCT_NAME ?? "AdCraft AI",
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  },
  experimental: {
    // A full generate runs 45-160s; Next kills proxied requests at 30s by default.
    proxyTimeout: 300_000,
    // The editor posts scene images as base64 data URLs (a few MB). Next 15 only caps
    // proxied bodies when middleware exists (middlewareClientMaxBodySize); there is
    // none here. If middleware is ever added, raise that limit or uploads will 413.
  },
  async rewrites() {
    // Unbuilt screens (P0-6) answer a real 404: rewritten before routing to a path that
    // doesn't exist. (A notFound() inside the page renders the 404 screen but with HTTP 200,
    // because the client settings layout has already started streaming.)
    const unfinished =
      process.env.NEXT_PUBLIC_SHOW_UNFINISHED === "1"
        ? []
        : UNFINISHED_ROUTES.map((source) => ({ source, destination: "/__not-built" }));
    return {
      beforeFiles: unfinished,
      afterFiles: [{ source: "/api/:path((?!v1/).*)", destination: `${VIDEO_APP_ORIGIN}/api/:path` }],
      fallback: [],
    };
  },
};

export default nextConfig;
