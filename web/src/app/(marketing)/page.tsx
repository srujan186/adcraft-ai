import Link from "next/link";
import HeroForm from "./components/HeroForm";
import Reveal from "./components/Reveal";
import Faq from "./components/Faq";
import { FAQ } from "./content/faq";

const STEPS = [
  {
    icon: "🔗",
    title: "Paste your URL",
    desc: "We read your real logo, colours, tagline and copy straight off the page. No uploads, no brand kit.",
  },
  {
    icon: "✍️",
    title: "AI writes the script",
    desc: "GPT-OSS 120B drafts a voiceover tuned to your brand, your chosen style and your exact ad length.",
  },
  {
    icon: "🎬",
    title: "We render the MP4",
    desc: "Kokoro narrates it, a licensed bed scores it, FFmpeg renders it. Download it the moment it lands.",
  },
];

const STYLES = [
  { name: "Modern", desc: "clean, confident" },
  { name: "Bold", desc: "high energy" },
  { name: "Minimal", desc: "one big idea" },
  { name: "Playful", desc: "fun, friendly" },
];

// Every figure below is read out of the backend — see ../CLAUDE.md.
const OUTPUT_SPEC = [
  { k: "Resolution", v: "1280 × 720" },
  { k: "Video", v: "H.264" },
  { k: "Audio", v: "AAC 128 kbps" },
  { k: "Frame rate", v: "30 fps" },
];

const FACTS = [
  { label: "No signup" },
  { value: "Free", label: "while in beta" },
  { value: "720p", label: "MP4 download" },
  { value: "15s / 30s", label: "ad lengths" },
  { value: "4", label: "ad styles" },
];

const GALLERY = [
  { icon: "🛍️", label: "E-commerce", meta: "15s · Bold" },
  { icon: "🍽️", label: "Restaurant", meta: "30s · Playful" },
  { icon: "💪", label: "Fitness studio", meta: "15s · Bold" },
  { icon: "🏥", label: "Healthcare", meta: "30s · Modern" },
  { icon: "🏠", label: "Real estate", meta: "30s · Modern" },
  { icon: "💻", label: "SaaS product", meta: "15s · Minimal" },
  { icon: "☕", label: "Local café", meta: "15s · Playful" },
  { icon: "🚗", label: "Automotive", meta: "30s · Bold" },
  { icon: "🎓", label: "Education", meta: "30s · Modern" },
  { icon: "💇", label: "Salon & spa", meta: "15s · Playful" },
];

// Fixed heights so the waveform is identical on server and client.
const WAVE = [22, 38, 54, 30, 66, 44, 78, 52, 34, 60, 26, 46, 70, 40, 24, 56, 32, 48];

export default function LandingPage() {
  return (
    <>
      {/* ── Hero ──────────────────────────────────────────────────────────
          The dark panel dissolves into the white page at its bottom edge, so
          the next section reads as lit rather than as a hard seam. */}
      <section className="hero">
        <div className="container hero-inner">
          <div className="hero-copy">
            <Reveal>
              <span className="badge badge-glass" style={{ marginBottom: "1.5rem" }}>
                URL in, MP4 out
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

          <Reveal delay={220}>
            <AdMock />
          </Reveal>
        </div>
      </section>

      {/* ── Fact strip — verifiable product facts only, no social proof ──── */}
      <div className="container">
        <div className="trust-strip">
          {FACTS.map((fact, i) => (
            <span className="trust-item" key={fact.label}>
              {i > 0 && <span className="trust-sep" aria-hidden="true">·</span>}
              {fact.value && <b>{fact.value}</b>}
              {fact.label}
            </span>
          ))}
        </div>
      </div>

      {/* ── How it works ──────────────────────────────────────────────────── */}
      <section className="section" id="how-it-works">
        <div className="container">
          <Reveal>
            <div className="section-head">
              <span className="eyebrow">How it works</span>
              <h2 className="h2">
                Three steps. One minute.
                <br />
                One finished video.
              </h2>
              <p className="lead" style={{ marginTop: "1.1rem" }}>
                No editing timeline, no stock-footage hunting, no voice actor.
                Everything is generated from the website you already have.
              </p>
            </div>
          </Reveal>

          <div className="flow">
            {STEPS.map((step, i) => (
              <Reveal key={step.title} delay={i * 90}>
                <div className="flow-item">
                  <div className="flow-tile" aria-hidden="true">{step.icon}</div>
                  <span className="flow-step nums">Step {String(i + 1).padStart(2, "0")}</span>
                  <h3 className="flow-title">{step.title}</h3>
                  <p className="flow-desc">{step.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── Bento — what is actually in the render ────────────────────────── */}
      <section className="section section-alt" id="styles">
        <div className="container">
          <Reveal>
            <div className="section-head">
              <span className="eyebrow">What you get</span>
              <h2 className="h2">Every knob worth turning, and nothing else</h2>
              <p className="lead" style={{ marginTop: "1.1rem" }}>
                Four tones, two lengths, four voices, five beds. Change one and the
                script, pacing and music all move with it.
              </p>
            </div>
          </Reveal>

          <div className="bento">
            <Reveal className="b-wide">
              <article className="bento-tile t-dark b-wide grain" style={{ height: "100%" }}>
                <div className="bento-vis vis-styles">
                  {STYLES.map((s) => (
                    <span className="vis-style" key={s.name}>
                      {s.name} <small>{s.desc}</small>
                    </span>
                  ))}
                </div>
                <div className="bento-body">
                  <span className="bento-kicker">Ad styles · 4</span>
                  <h3 className="bento-title">Pick the tone that fits your brand</h3>
                  <p className="bento-desc">
                    The same business, four completely different ads. The style is
                    passed to the script model, not bolted on afterwards.
                  </p>
                </div>
              </article>
            </Reveal>

            <Reveal className="b-mid">
              <article className="bento-tile t-mint b-mid" style={{ height: "100%" }}>
                <div className="bento-vis">
                  <p className="vis-big">
                    15<em>s</em> / 30<em>s</em>
                  </p>
                </div>
                <div className="bento-body">
                  <span className="bento-kicker">Durations · 2</span>
                  <h3 className="bento-title">Two lengths, both cut to time</h3>
                  <p className="bento-desc">
                    The script is written to the duration you pick, so narration
                    never runs long and never leaves dead air at the end.
                  </p>
                </div>
              </article>
            </Reveal>

            <Reveal className="b-mid">
              <article className="bento-tile t-ice b-mid" style={{ height: "100%" }}>
                <div className="bento-vis vis-eq" aria-hidden="true">
                  <i /><i /><i /><i /><i />
                </div>
                <div className="bento-body">
                  <span className="bento-kicker">Music beds · 5</span>
                  <h3 className="bento-title">Royalty-free music, matched to the style</h3>
                  <p className="bento-desc">
                    Five licensed beds ship with the renderer. The style you choose
                    picks the bed and sets the duck level under the voice.
                  </p>
                </div>
              </article>
            </Reveal>

            <Reveal className="b-wide">
              <article className="bento-tile t-lavender b-wide" style={{ height: "100%" }}>
                <div className="bento-vis vis-wave" aria-hidden="true">
                  {WAVE.map((h, i) => (
                    <i key={i} style={{ height: `${h}%` }} />
                  ))}
                </div>
                <div className="bento-body">
                  <span className="bento-kicker">Voices · 4</span>
                  <h3 className="bento-title">Narration that runs on our own machine</h3>
                  <p className="bento-desc">
                    Kokoro synthesises the voiceover locally — four voices, no
                    third-party TTS queue between you and the render.
                  </p>
                </div>
              </article>
            </Reveal>

            <Reveal className="b-full">
              <article className="bento-tile b-full" style={{ height: "100%" }}>
                <dl className="bento-vis vis-spec">
                  {OUTPUT_SPEC.map((row) => (
                    <div className="spec-row" key={row.k}>
                      <dt>{row.k}</dt>
                      <dd>{row.v}</dd>
                    </div>
                  ))}
                </dl>
                <div className="bento-body">
                  <span className="bento-kicker">Output</span>
                  <h3 className="bento-title">A plain MP4 you own outright</h3>
                  <p className="bento-desc">
                    No watermark, no export tier, no rendering credits. It downloads
                    straight to your machine and plays anywhere.
                  </p>
                </div>
              </article>
            </Reveal>
          </div>
        </div>
      </section>

      {/* ── Gallery marquee ───────────────────────────────────────────────── */}
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
                  <span className="marquee-icon" aria-hidden="true">{item.icon}</span>
                  <span>
                    <span className="marquee-label">{item.label}</span>
                    <span className="marquee-meta" style={{ display: "block" }}>{item.meta}</span>
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="marquee marquee-rev">
            <div className="marquee-track">
              {[...GALLERY.slice().reverse(), ...GALLERY.slice().reverse()].map((item, i) => (
                <div className="marquee-card" key={`b${i}`}>
                  <span className="marquee-icon" aria-hidden="true">{item.icon}</span>
                  <span>
                    <span className="marquee-label">{item.label}</span>
                    <span className="marquee-meta" style={{ display: "block" }}>{item.meta}</span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Reveal>

        <div className="container" style={{ textAlign: "center", marginTop: "3rem" }}>
          <Reveal>
            <Link href="/generate" className="btn btn-primary btn-lg">
              Generate your ad
            </Link>
          </Reveal>
        </div>
      </section>

      {/* ── FAQ ───────────────────────────────────────────────────────────── */}
      <section className="section section-alt" id="faq">
        <div className="container container-narrow">
          <Reveal>
            <div className="section-head">
              <span className="eyebrow">FAQ</span>
              <h2 className="h2">Questions, answered</h2>
              <p className="lead" style={{ marginTop: "1.1rem" }}>
                What it costs, how long it takes, and what it does with your site.
              </p>
            </div>
          </Reveal>

          <Reveal>
            <Faq items={FAQ.slice(0, 8)} />
          </Reveal>

          <Reveal>
            <p className="hint" style={{ marginTop: "1.75rem" }}>
              More in the{" "}
              <Link href="/resources/help" className="link-arrow" style={{ fontSize: "inherit" }}>
                help centre <span className="arrow">→</span>
              </Link>
            </p>
          </Reveal>
        </div>
      </section>

      {/* ── Pricing / final CTA ───────────────────────────────────────────── */}
      <section className="section" id="pricing" style={{ paddingTop: 0 }}>
        <div className="container">
          <Reveal>
            <div className="cta-panel">
              <h2 className="h2 cta-title">
                Ready to dive in?
                <br />
                <em>Paste a URL.</em>
              </h2>
              <p className="cta-sub" style={{ marginBottom: "2.75rem" }}>
                No credit card, no account, no export tier. Free while we&apos;re in
                beta — and the MP4 is yours either way.
              </p>

              <div className="stat-row" style={{ marginBottom: "2.75rem" }}>
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

              <div className="cta-actions">
                <Link href="/generate" className="btn btn-lime btn-lg" id="pricing-cta-btn">
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

/* A framed still of the kind of render the pipeline produces. Illustrative —
   the brand in it is invented, and it carries no claims or metrics. */
function AdMock() {
  return (
    <div className="mock" aria-hidden="true">
      <div className="mock-bar">
        <span className="mock-dot" />
        <span className="mock-dot" />
        <span className="mock-dot" />
        <span className="mock-url">northline.supply</span>
        <span className="mock-tag">Sample render</span>
      </div>

      <div className="mock-frame">
        <span className="mock-brand">
          <i>N</i> Northline Supply
        </span>
        <span className="mock-play" />
        <span>
          <span className="mock-kicker">
            Workwear that <em>outlasts</em> the job.
          </span>
          <span className="mock-caption">Voiceover · Modern · 15s</span>
        </span>
      </div>

      <div className="mock-scrub">
        <span className="mock-scrub-bar"><b /></span>
        <span className="mock-time">0:07 / 0:15</span>
      </div>

      <div className="mock-tracks">
        <div className="mock-track mock-track-a"><span>Script</span><b /></div>
        <div className="mock-track mock-track-b"><span>Voice</span><b /></div>
        <div className="mock-track mock-track-c"><span>Music</span><b /></div>
      </div>
    </div>
  );
}
