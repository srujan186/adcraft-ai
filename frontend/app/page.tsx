import Link from "next/link";

const features = [
  {
    icon: "🔗",
    title: "Paste Any URL",
    desc: "We screenshot your website and extract your brand identity — colors, logo, tagline — automatically.",
  },
  {
    icon: "✍️",
    title: "AI Writes the Script",
    desc: "Llama 3.3 70B crafts a punchy voiceover script tailored to your brand style and video duration.",
  },
  {
    icon: "🎬",
    title: "Video in Seconds",
    desc: "Kokoro TTS narrates the ad, Pexels stock footage fills the scenes, and we assemble your MP4 live.",
  },
];

export default function LandingPage() {
  return (
    <div className="section">
      {/* ── Hero ──────────────────────────────────────────────────── */}
      <div className="container">
        <section className="hero">
          <div className="hero-eyebrow fade-up">
            <span>⚡</span> AI-Powered Ad Generation
          </div>

          <h1 className="hero-title fade-up fade-up-d1">
            Turn any website into a<br />
            <span className="grad">stunning video ad</span>
          </h1>

          <p className="hero-subtitle fade-up fade-up-d2">
            Paste a URL. Choose your style. Get a broadcast-ready MP4 in under
            a minute — no editing skills required.
          </p>

          <div className="hero-cta fade-up fade-up-d3">
            <Link href="/generate" className="btn btn-primary btn-lg" id="hero-cta-btn">
              🎬 Create Your Ad — Free
            </Link>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-secondary btn-lg"
              id="hero-api-btn"
            >
              📖 API Docs
            </a>
          </div>
        </section>

        {/* ── Trust bar ────────────────────────────────────────────── */}
        <div className="trust-bar">
          <span className="trust-item">✅ No signup required</span>
          <span className="trust-item">⚡ Groq-powered LLM</span>
          <span className="trust-item">🎙️ Kokoro TTS voice</span>
          <span className="trust-item">🎵 Royalty-free music</span>
          <span className="trust-item">📱 MP4 download</span>
        </div>

        {/* ── Features ─────────────────────────────────────────────── */}
        <section style={{ padding: "5rem 0" }}>
          <div style={{ textAlign: "center", marginBottom: "3rem" }}>
            <h2 className="section-title">How it works</h2>
            <p className="section-sub">Three steps. One minute. One video.</p>
          </div>
          <div className="features-grid">
            {features.map((f) => (
              <div key={f.title} className="card fade-up">
                <span className="feature-icon">{f.icon}</span>
                <p className="feature-title">{f.title}</p>
                <p className="feature-desc">{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── Bottom CTA ───────────────────────────────────────────── */}
        <section
          style={{
            textAlign: "center",
            padding: "4rem 0 7rem",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "1.5rem",
          }}
        >
          <div className="badge">✨ Completely free to try</div>
          <h2 className="section-title">Ready to create your first ad?</h2>
          <p className="section-sub" style={{ maxWidth: 420 }}>
            No credit card. No account. Just paste your URL and hit generate.
          </p>
          <Link
            href="/generate"
            className="btn btn-primary btn-lg"
            id="bottom-cta-btn"
          >
            🚀 Get Started Now
          </Link>
        </section>
      </div>
    </div>
  );
}
