import type { Metadata } from "next";

import AnnounceBar from "./components/AnnounceBar";
import SiteFooter from "./components/SiteFooter";
import SiteHeader from "./components/SiteHeader";
import "./legacy.css";

// The public marketing site + free Creative Studio (/ → /generate → /result), moved
// from frontend/. Its stylesheet is scoped under .mk so it can't collide with the
// platform's Tailwind UI; fonts (Inter + Inter Tight) come from the root layout.
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
};

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mk">
      <a className="skip-link" href="#main">Skip to content</a>
      <AnnounceBar />
      <SiteHeader />
      <main id="main">{children}</main>
      <SiteFooter />
    </div>
  );
}
