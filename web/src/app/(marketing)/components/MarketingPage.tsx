import Link from "next/link";
import Reveal from "./Reveal";
import type { MarketingContent } from "../content/types";

const STEPS = [
  { n: 1, title: "Paste your URL", desc: "We read your logo, colours and copy straight off the page." },
  { n: 2, title: "Pick style & length", desc: "Four tones, fifteen or thirty seconds." },
  { n: 3, title: "Download the MP4", desc: "Narrated, scored and rendered — usually in under a minute." },
];

export default function MarketingPage({ content }: { content: MarketingContent }) {
  return (
    <>
      {/* Hero — dark block off the top, white body below it */}
      <section className="page-hero">
        <div className="container container-narrow">
          <Reveal>
            <span className="eyebrow">{content.eyebrow}</span>
            <h1 className="h1" style={{ fontSize: "clamp(2rem, 4.4vw, 3.4rem)" }}>
              {content.title}
            </h1>
            <p className="lead" style={{ marginTop: "1rem" }}>{content.lead}</p>
          </Reveal>

          <Reveal delay={80}>
            <div className="page-hero-actions">
              <Link href="/generate" className="btn btn-lime btn-lg">
                Generate your ad
              </Link>
              <Link href="/#how-it-works" className="btn btn-glass btn-lg">
                See how it works
              </Link>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Body */}
      <section className="section">
        <div className="container">
          <Reveal>
            <p className="lead" style={{ maxWidth: 760, marginBottom: "3rem" }}>
              {content.intro}
            </p>
          </Reveal>

          <div className="grid grid-3">
            {content.points.map((p, i) => (
              <Reveal key={p.title} delay={i * 80}>
                <div className="card card-hover" style={{ height: "100%" }}>
                  <p className="feature-title">{p.title}</p>
                  <p className="feature-desc">{p.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>

          {content.suggested && (
            <Reveal>
              <div className="card" style={{ marginTop: "2rem", background: "var(--surface2)" }}>
                <p className="mega-col-title" style={{ marginBottom: "0.85rem" }}>
                  Suggested starting point
                </p>
                <div className="chip-grid">
                  <span className="chip">Style <span className="chip-count">{content.suggested.style}</span></span>
                  <span className="chip">Length <span className="chip-count">{content.suggested.duration}</span></span>
                  <span className="chip">Music <span className="chip-count">{content.suggested.music}</span></span>
                </div>
                <p className="hint" style={{ marginTop: "0.85rem" }}>
                  A suggestion, not a rule — every setting is changeable, and you can
                  regenerate as many times as you like.
                </p>
              </div>
            </Reveal>
          )}
        </div>
      </section>

      {/* How it works recap */}
      <section className="section section-alt">
        <div className="container">
          <Reveal>
            <div className="section-head center">
              <span className="eyebrow">How it works</span>
              <h2 className="h2">Three steps, start to finish</h2>
            </div>
          </Reveal>
          <div className="grid grid-3">
            {STEPS.map((s, i) => (
              <Reveal key={s.n} delay={i * 80}>
                <div className="card" style={{ height: "100%" }}>
                  <div className="step-num">{s.n}</div>
                  <p className="feature-title">{s.title}</p>
                  <p className="feature-desc">{s.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* CTA — an inset panel, not a full-bleed band: the footer is already
          dark, and two adjoining dark bands read as one shapeless block. */}
      <section className="section">
        <div className="container">
          <Reveal>
            <div className="cta-panel">
              <h2 className="h2 cta-title">
                Try it on <em>your own site</em>
              </h2>
              <p className="cta-sub" style={{ marginBottom: "2.25rem" }}>
                Free while in beta. No account, no card, no watermark on the render.
              </p>
              <div className="cta-actions">
                <Link href="/generate" className="btn btn-lime btn-lg">
                  Get started free
                </Link>
                <Link href="/#how-it-works" className="btn btn-glass btn-lg">
                  See how it works
                </Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
