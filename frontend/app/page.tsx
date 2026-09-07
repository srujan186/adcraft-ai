import Link from "next/link";
import HeroForm from "./components/HeroForm";
import Reveal from "./components/Reveal";
import Faq from "./components/Faq";
import { FAQ } from "./content/faq";

const STEPS = [
  {
    icon: "🔗",
    title: "Paste your URL",
    desc: "We screenshot your site and pull out your real logo, colours, tagline and copy — no uploads, no brand kit needed.",
  },
  {
    icon: "✍️",
    title: "AI writes the script",
    desc: "Llama 3.3 70B writes a punchy voiceover tuned to your brand, your chosen style and your exact ad length.",
  },
  {
    icon: "🎬",
    title: "We assemble the video",
    desc: "Kokoro narrates it, licensed music scores it, and FFmpeg renders a finished MP4 you can download instantly.",
  },
];

const STYLES = [
  { emoji: "✨", name: "Modern",  desc: "Clean, professional, confident" },
  { emoji: "⚡", name: "Bold",    desc: "High energy, punchy, exciting" },
  { emoji: "◻️", name: "Minimal", desc: "Simple, elegant, one big idea" },
  { emoji: "🎉", name: "Playful", desc: "Fun, friendly, approachable" },
];

const CAPABILITIES = [
  { label: "Ad styles", count: "4" },
  { label: "Durations", count: "15s / 30s" },
  { label: "Music beds", count: "5" },
  { label: "Voice options", count: "4" },
  { label: "Output", count: "720p MP4" },
];

const GALLERY = [
  { icon: "🛍️", label: "E-commerce",   meta: "15s · Bold" },
  { icon: "🍽️", label: "Restaurant",   meta: "30s · Playful" },
  { icon: "💪", label: "Fitness studio", meta: "15s · Bold" },
  { icon: "🏥", label: "Healthcare",   meta: "30s · Modern" },
  { icon: "🏠", label: "Real estate",  meta: "30s · Modern" },
  { icon: "💻", label: "SaaS product", meta: "15s · Minimal" },
  { icon: "☕", label: "Local café",    meta: "15s · Playful" },
  { icon: "🚗", label: "Automotive",   meta: "30s · Bold" },
  { icon: "🎓", label: "Education",    meta: "30s · Modern" },
  { icon: "💇", label: "Salon & spa",  meta: "15s · Playful" },
];

export default function LandingPage() {
  return (
    <>
      {/* ── Hero ──────────────────────────────────────────────────────── */}
      <section className="hero">
        <div className="container">
          <Reveal>
            <span className="badge" style={{ marginBottom: "1.5rem" }}>
              ⚡ AI-powered ad generation
            </span>
          </Reveal>

          <Reveal delay={60}>
            <h1 className="h1 hero-title">
              No creative team?
              <br />
              <span className="grad">No problem.</span>
            </h1>
          </Reveal>

          <Reveal delay={120}>
            <p className="hero-sub">
              Type your business URL and we&apos;ll turn it into a finished video
              ad — script, voiceover, music and all — in under a minute.
            </p>
          </Reveal>

          <Reveal delay={180}>
            <HeroForm />
          </Reveal>
        </div>
      </section>

      {/* ── Trust strip — verifiable product facts only ────────────────── */}
      <div className="container">
        <div className="trust-strip">
          <span className="trust-item">✅ No signup required</span>
          <span className="trust-item">💸 Free while in beta</span>
          <span className="trust-item">🎬 720p MP4 download</span>
          <span className="trust-item">⏱️ 15 or 30 seconds</span>
          <span className="trust-item">🎨 4 ad styles</span>
        </div>
      </div>

      {/* ── How it works ──────────────────────────────────────────────── */}
      <section className="section" id="how-it-works">
        <div className="container">
          <Reveal>
            <div className="section-head center">
              <span className="eyebrow">How it works</span>
              <h2 className="h2">Three steps. One minute. One video.</h2>
              <p className="lead" style={{ marginTop: "0.85rem" }}>
                No editing timeline, no stock footage hunting, no voice actor.
                Everything is generated from the website you already have.
              </p>
            </div>
          </Reveal>

          <div className="grid grid-3">
            {STEPS.map((step, i) => (
              <Reveal key={step.title} delay={i * 90}>
                <div className="card card-hover" style={{ height: "100%" }}>
                  <div className="step-num">{i + 1}</div>
                  <div className="feature-icon">{step.icon}</div>
                  <p className="feature-title">{step.title}</p>
                  <p className="feature-desc">{step.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── Ad styles ─────────────────────────────────────────────────── */}
      <section className="section section-alt" id="styles">
        <div className="container">
          <Reveal>
            <div className="section-head center">
              <span className="eyebrow">Ad styles</span>
              <h2 className="h2">Pick the tone that fits your brand</h2>
              <p className="lead" style={{ marginTop: "0.85rem" }}>
                The same business, four completely different ads. Switch the
                style and the script, pacing and music all change with it.
              </p>
            </div>
          </Reveal>

          <div className="grid grid-4" style={{ marginBottom: "2.5rem" }}>
            {STYLES.map((style, i) => (
              <Reveal key={style.name} delay={i * 70}>
                <div className="card card-hover" style={{ height: "100%" }}>
                  <div className="feature-icon">{style.emoji}</div>
                  <p className="feature-title">{style.name}</p>
                  <p className="feature-desc">{style.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>

          <Reveal>
            <div className="chip-grid" style={{ justifyContent: "center" }}>
              {CAPABILITIES.map((cap) => (
                <span key={cap.label} className="chip">
                  {cap.label}
                  <span className="chip-count">{cap.count}</span>
                </span>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── Gallery marquee ───────────────────────────────────────────── */}
      <section className="section">
        <div className="container">
          <Reveal>
            <div className="section-head center">
              <span className="eyebrow">Works for any business</span>
              <h2 className="h2">Built for whatever you sell</h2>
            </div>
          </Reveal>
        </div>

        <Reveal>
          <div className="marquee" style={{ marginBottom: "1rem" }}>
            <div className="marquee-track">
              {[...GALLERY, ...GALLERY].map((item, i) => (
                <div className="marquee-card" key={`a${i}`}>
                  <span className="marquee-icon">{item.icon}</span>
                  <span className="marquee-label">{item.label}</span>
                  <span className="marquee-meta">{item.meta}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="marquee marquee-rev">
            <div className="marquee-track">
              {[...GALLERY.slice().reverse(), ...GALLERY.slice().reverse()].map((item, i) => (
                <div className="marquee-card" key={`b${i}`}>
                  <span className="marquee-icon">{item.icon}</span>
                  <span className="marquee-label">{item.label}</span>
                  <span className="marquee-meta">{item.meta}</span>
                </div>
              ))}
            </div>
          </div>
        </Reveal>

        <div className="container" style={{ textAlign: "center", marginTop: "3rem" }}>
          <Reveal>
            <Link href="/generate" className="btn btn-primary btn-lg">
              🎬 Generate your ad
            </Link>
          </Reveal>
        </div>
      </section>

      {/* ── FAQ ───────────────────────────────────────────────────────── */}
      <section className="section section-alt" id="faq">
        <div className="container container-narrow">
          <Reveal>
            <div className="section-head center">
              <span className="eyebrow">FAQ</span>
              <h2 className="h2">Questions, answered</h2>
              <p className="lead" style={{ marginTop: "0.85rem" }}>
                What it costs, how long it takes, and what it does with your site.
              </p>
            </div>
          </Reveal>

          <Reveal>
            <Faq items={FAQ.slice(0, 8)} />
          </Reveal>

          <Reveal>
            <p className="hint" style={{ textAlign: "center", marginTop: "1.75rem" }}>
              More in the{" "}
              <Link href="/resources/help" style={{ color: "var(--accent)", fontWeight: 600 }}>
                help centre
              </Link>.
            </p>
          </Reveal>
        </div>
      </section>

      {/* ── Pricing / final CTA ───────────────────────────────────────── */}
      <section className="section section-dark" id="pricing">
        <div className="container">
          <Reveal>
            <div className="section-head center">
              <h2 className="h2" style={{ color: "#fff" }}>Ready to dive in?</h2>
              <p className="lead" style={{ color: "rgba(255,255,255,0.65)", marginTop: "0.85rem" }}>
                No credit card. No account. Paste a URL and hit generate.
              </p>
            </div>
          </Reveal>

          <Reveal>
            <div className="stat-row" style={{ marginBottom: "2.5rem" }}>
              <div className="stat">
                <p className="stat-val">Free</p>
                <p className="stat-label">While in beta</p>
              </div>
              <div className="stat">
                <p className="stat-val">15s / 30s</p>
                <p className="stat-label">Ad lengths</p>
              </div>
              <div className="stat">
                <p className="stat-val">720p</p>
                <p className="stat-label">MP4 download</p>
              </div>
            </div>
          </Reveal>

          <Reveal>
            <div style={{ display: "flex", gap: "0.85rem", justifyContent: "center", flexWrap: "wrap" }}>
              <Link href="/generate" className="btn btn-primary btn-lg" id="pricing-cta-btn">
                🚀 Get started free
              </Link>
              <Link href="/#how-it-works" className="btn btn-secondary btn-lg">
                See how it works
              </Link>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
