import type { Metadata } from "next";
import Link from "next/link";
import Faq from "../../components/Faq";
import { FAQ } from "../../content/faq";

export const metadata: Metadata = {
  title: "Help centre — AdCraft AI",
  description:
    "Answers to common questions about generating video ads with AdCraft — cost, timing, formats, editing and the API.",
};

const GUIDES = [
  {
    title: "Generating your first ad",
    steps: [
      "Paste your business URL on the generate page — a bare domain like yourbusiness.com is fine.",
      "Pick an ad style. Modern is the safest default; Bold suits promotions and offers.",
      "Choose fifteen or thirty seconds. Fifteen works better for social placements.",
      "Hit generate and wait. The stepper shows scraping, scripting and building as they happen.",
    ],
  },
  {
    title: "Getting better brand detection",
    steps: [
      "Point at your homepage first — it usually carries the most branding signal.",
      "A theme-color meta tag is the single strongest hint for your primary colour.",
      "An apple-touch-icon gives a much better logo than a favicon, which is often too small.",
      "If detection still misses, override the colours directly in the editor.",
    ],
  },
  {
    title: "Choosing a style and length",
    steps: [
      "Modern — clean and professional. Good for services, healthcare, B2B.",
      "Bold — high energy and punchy. Good for offers, fitness, automotive.",
      "Minimal — one big idea, cleanly delivered. Good for software and premium brands.",
      "Playful — friendly and approachable. Good for hospitality, salons, local business.",
    ],
  },
];

export default function HelpPage() {
  return (
    <>
      <section className="section" style={{ paddingBottom: "2rem" }}>
        <div className="container container-narrow">
          <span className="eyebrow">Help centre</span>
          <h1 className="h1" style={{ fontSize: "clamp(2rem, 4.4vw, 3.1rem)" }}>
            Questions & answers
          </h1>
          <p className="lead" style={{ marginTop: "1rem" }}>
            How AdCraft works, what it produces, and what it does with your site.
          </p>
        </div>
      </section>

      <section className="section" style={{ paddingTop: 0 }}>
        <div className="container container-narrow">
          <Faq items={FAQ} />
        </div>
      </section>

      <section className="section section-alt" id="guides">
        <div className="container container-narrow">
          <div className="section-head">
            <span className="eyebrow">Guides</span>
            <h2 className="h2">Getting the most out of it</h2>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            {GUIDES.map((g) => (
              <div className="card" key={g.title}>
                <p className="feature-title" style={{ marginBottom: "0.85rem" }}>{g.title}</p>
                <ol className="guide-list">
                  {g.steps.map((s) => <li key={s}>{s}</li>)}
                </ol>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section" id="contact">
        <div className="container container-narrow">
          <div className="card card-pad-lg" style={{ textAlign: "center" }}>
            <h2 className="h3" style={{ marginBottom: "0.6rem" }}>Still stuck?</h2>
            <p className="feature-desc" style={{ marginBottom: "1.5rem" }}>
              AdCraft is in active development. If something is broken or a site
              will not scrape, that is useful to know.
            </p>
            <div style={{ display: "flex", gap: "0.75rem", justifyContent: "center", flexWrap: "wrap" }}>
              <Link href="/resources/api" className="btn btn-secondary">API reference</Link>
              <Link href="/generate" className="btn btn-primary">Try generating an ad</Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
