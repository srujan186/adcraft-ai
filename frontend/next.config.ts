import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
