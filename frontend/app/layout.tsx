import type { Metadata } from "next";
import { Inter, Inter_Tight } from "next/font/google";
import "./globals.css";
import AnnounceBar from "./components/AnnounceBar";
import SiteHeader from "./components/SiteHeader";
import SiteFooter from "./components/SiteFooter";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

// Display face. Inter Tight's narrower widths let the big headlines sit at
// -0.04em tracking without the counters closing up.
const display = Inter_Tight({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-display",
});

export const metadata: Metadata = {
  title: "AdCraft AI — Turn any URL into a video ad",
  description:
    "Paste your business URL and get a polished, broadcast-ready video ad in under a minute. Powered by AI.",
  openGraph: {
    title: "AdCraft AI — Turn any URL into a video ad",
    description:
      "Paste your business URL and get a narrated 720p MP4 video ad in under a minute. Free while in beta.",
    siteName: "AdCraft AI",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "AdCraft AI — Turn any URL into a video ad",
    description:
      "Paste your business URL and get a narrated 720p MP4 video ad in under a minute.",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${display.variable}`}>
      {/* Browser extensions (Grammarly, password managers) inject attributes
          into <body> before React hydrates. This suppresses that false
          positive; it applies one level deep only, so real mismatches
          inside the app still surface. */}
      <body suppressHydrationWarning>
        <a className="skip-link" href="#main">Skip to content</a>
        <AnnounceBar />
        <SiteHeader />
        <main id="main">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
