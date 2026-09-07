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
      {/* Hero */}
      <section className="section" style={{ paddingBottom: "2rem" }}>
        <div className="container container-narrow">
          <Reveal>
            <span className="eyebrow">{content.eyebrow}</span>
            <h1 className="h1" style={{ fontSize: "clamp(2rem, 4.4vw, 3.1rem)" }}>
              {content.title}
            </h1>
            <p className="lead" style={{ marginTop: "1rem" }}>{content.lead}</p>
          </Reveal>

          <Reveal delay={80}>
            <div style={{ display: "flex", gap: "0.75rem", marginTop: "2rem", flexWrap: "wrap" }}>
              <Link href="/generate" className="btn btn-primary btn-lg">
                🎬 Generate your ad
              </Link>
              <Link href="/#how-it-works" className="btn btn-secondary btn-lg">
                See how it works
              </Link>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Body */}
      <section className="section" style={{ paddingTop: "1rem" }}>
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

      {/* CTA */}
      <section className="section section-dark">
        <div className="container">
          <Reveal>
            <div className="section-head center" style={{ marginBottom: "2rem" }}>
              <h2 className="h2" style={{ color: "#fff" }}>Try it on your own site</h2>
              <p className="lead" style={{ color: "rgba(255,255,255,0.65)", marginTop: "0.75rem" }}>
                Free while in beta. No account, no card.
              </p>
            </div>
          </Reveal>
          <Reveal>
            <div style={{ display: "flex", justifyContent: "center" }}>
              <Link href="/generate" className="btn btn-primary btn-lg">
                🚀 Get started free
              </Link>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
