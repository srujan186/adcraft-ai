import type { Metadata } from "next";
import { Inter, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import AnnounceBar from "./components/AnnounceBar";
import SiteHeader from "./components/SiteHeader";
import SiteFooter from "./components/SiteFooter";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const display = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-display",
});

export const metadata: Metadata = {
  title: "AdCraft AI — Turn any URL into a video ad",
  description:
    "Paste your business URL and get a polished, broadcast-ready video ad in under a minute. Powered by AI.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${display.variable}`}>
      {/* Browser extensions (Grammarly, password managers) inject attributes
          into <body> before React hydrates. This suppresses that false
          positive; it applies one level deep only, so real mismatches
          inside the app still surface. */}
      <body suppressHydrationWarning>
        <AnnounceBar />
        <SiteHeader />
        <main>{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
