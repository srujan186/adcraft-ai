import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "AdCraft AI — Generate Video Ads in Seconds",
  description: "Paste any business URL and get a polished video ad in under a minute. Powered by AI.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="nav">
          <Link className="nav-logo" href="/">⚡ AdCraft AI</Link>
          <div className="nav-links">
            <Link className="nav-link" href="/">Home</Link>
            <Link className="nav-link" href="/generate">Create Ad</Link>
          </div>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
