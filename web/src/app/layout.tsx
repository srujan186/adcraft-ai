import type { Metadata } from "next";
import localFont from "next/font/local";

import { Providers } from "./providers";
import "./globals.css";

// Fonts are bundled, not fetched from Google at build time: next/font/google
// downloads from fonts.googleapis.com during every build, which fails the Vercel
// build whenever that fetch is briefly unreachable. These variable woff2 files
// (OFL, from Fontsource) cover every weight with no network dependency.
const inter = localFont({
  src: "./fonts/Inter-Variable.woff2",
  variable: "--font-inter",
  display: "swap",
  weight: "100 900",
});
// Display face for the marketing site's headlines (app/(marketing)). On <html> so
// its portals (drawer, generating overlay) get it too.
const display = localFont({
  src: "./fonts/InterTight-Variable.woff2",
  variable: "--font-display",
  display: "swap",
  weight: "100 900",
});

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
