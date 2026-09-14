import type { NextConfig } from "next";

// Where the FastAPI backend lives. Only used to proxy — it never reaches the
// browser, so the app is served from a single origin in dev and in Docker.
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Serve the API from the same origin as the app. This mirrors what
  // ../nginx.conf does for docker-compose, and means the browser makes no
  // cross-origin requests at all: no CORS preflights, and the <video> used for
  // scene thumbnails is same-origin so its canvas is never tainted.
  //
  // Set NEXT_PUBLIC_API_URL to an absolute URL to bypass this and talk to a
  // backend on another host (a Vercel frontend against a Render backend).
  experimental: {
    // A full generate runs 45-160s. Next kills a proxied request at 30s by
    // default, which returned a 500 mid-render. nginx.conf sets the same kind
    // of allowance (proxy_read_timeout 120s) for the docker-compose path.
    proxyTimeout: 300_000,
    // The editor posts scene images as base64 data URLs, so the body can be a
    // few MB. nginx.conf allows 50M for the same reason.
    proxyClientMaxBodySize: 50 * 1024 * 1024,
  },

  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND_ORIGIN}/api/:path*` },
      { source: "/docs",       destination: `${BACKEND_ORIGIN}/docs` },
      { source: "/openapi.json", destination: `${BACKEND_ORIGIN}/openapi.json` },
    ];
  },

  // NOTE: For self-hosted Docker deployment, change `output` to "standalone"
  // and rebuild. Vercel manages output automatically, so leave it unset here.

  // Allow images from the backend (add Oracle VM IP here when deploying)
  images: {
    remotePatterns: [
      { protocol: "http",  hostname: "localhost", port: "8000" },
      { protocol: "https", hostname: "**" },
    ],
  },
};

export default nextConfig;
