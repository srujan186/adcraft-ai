import type { Metadata } from "next";
import { Inter, Inter_Tight } from "next/font/google";

import { Providers } from "./providers";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
// Display face for the marketing site's headlines (app/(marketing)). On <html> so
// its portals (drawer, generating overlay) get it too.
const display = Inter_Tight({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--font-display", display: "swap" });

const PRODUCT = process.env.NEXT_PUBLIC_PRODUCT_NAME ?? "AdCraft AI";

export const metadata: Metadata = {
  title: `${PRODUCT} — Streaming TV advertising`,
  description: "Self-serve Connected-TV advertising for performance marketers.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${display.variable}`}>
      {/* Extensions (Grammarly, password managers) inject attributes into <body> pre-hydration. */}
      <body suppressHydrationWarning>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
