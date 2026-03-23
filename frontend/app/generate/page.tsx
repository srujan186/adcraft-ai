"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { generateVideo, type AdStyle } from "@/lib/api";

const STYLES: { key: AdStyle; name: string; emoji: string; desc: string }[] = [
  { key: "modern",  name: "Modern",  emoji: "✨", desc: "Clean, professional, confident" },
  { key: "bold",    name: "Bold",    emoji: "⚡", desc: "High energy, punchy, exciting" },
  { key: "minimal", name: "Minimal", emoji: "◻️", desc: "Simple, elegant, one big idea" },
  { key: "playful", name: "Playful", emoji: "🎉", desc: "Fun, friendly, approachable" },
];

const STEPS = [
  { label: "Scraping",  icon: "🔗" },
  { label: "Scripting", icon: "✍️" },
  { label: "Building",  icon: "🎬" },
  { label: "Done",      icon: "✅" },
];

export default function GeneratePage() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [style, setStyle] = useState<AdStyle>("modern");
  const [duration, setDuration] = useState<15 | 30>(15);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(-1);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) { setError("Please enter a URL"); return; }

    setError("");
    setLoading(true);

    // Simulate step progression based on timing
    setStep(0);
    const stepTimer1 = setTimeout(() => setStep(1), 8000);
    const stepTimer2 = setTimeout(() => setStep(2), 20000);

    try {
      const result = await generateVideo(url.trim(), style, duration);
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      setStep(3);
      // Store result and navigate
      sessionStorage.setItem("adcraft_result", JSON.stringify(result));
      router.push("/result");
    } catch (err: unknown) {
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      setStep(-1);
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="section" style={{ padding: "3rem 0 5rem" }}>
      <div className="container" style={{ maxWidth: 680 }}>
        {/* Header */}
        <div className="fade-up" style={{ marginBottom: "2.5rem" }}>
          <div className="badge" style={{ marginBottom: "1rem" }}>🚀 AI Ad Generator</div>
          <h1 className="section-title" style={{ fontSize: "2rem" }}>Create your video ad</h1>
          <p className="section-sub">
            Paste your business URL below. We&apos;ll handle everything else.
          </p>
        </div>

        {/* Progress stepper — visible while loading */}
        {loading && (
          <div
            className="card fade-up"
            style={{ marginBottom: "2rem", padding: "1.75rem" }}
            id="progress-stepper"
          >
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "1.25rem", textAlign: "center" }}>
              Generating your ad — this takes ~30–60 seconds
            </p>
            <div className="stepper">
              {STEPS.map((s, i) => (
                <div
                  key={s.label}
                  className={`step ${step === i ? "active" : step > i ? "done" : ""}`}
                >
                  <div className="step-icon">
                    {step > i ? "✓" : s.icon}
                  </div>
                  <span className="step-label">{s.label}</span>
                  {i < STEPS.length - 1 && <div className="step-line" />}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="card fade-up fade-up-d1" id="generate-form">
          {/* URL input */}
          <div className="input-wrap" style={{ marginBottom: "1.75rem" }}>
            <label htmlFor="url-input" className="label">Business URL</label>
            <div style={{ display: "flex", gap: "0.75rem" }}>
              <input
                id="url-input"
                className="input"
                type="text"
                placeholder="e.g. stripe.com or https://example.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={loading}
                autoFocus
              />
            </div>
            <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
              We&apos;ll screenshot your website and extract logo, colors &amp; brand info.
            </span>
          </div>

          <div className="divider" style={{ margin: "0 0 1.75rem" }} />

          {/* Style picker */}
          <div style={{ marginBottom: "1.75rem" }}>
            <p className="label" style={{ marginBottom: "0.75rem" }}>Ad Style</p>
            <div className="style-grid">
              {STYLES.map((s) => (
                <button
                  key={s.key}
                  type="button"
                  id={`style-${s.key}`}
                  className={`style-card ${style === s.key ? "selected" : ""}`}
                  onClick={() => setStyle(s.key)}
                  disabled={loading}
                >
                  <span className="style-card-name">{s.emoji} {s.name}</span>
                  <p className="style-card-desc">{s.desc}</p>
                </button>
              ))}
            </div>
          </div>

          <div className="divider" style={{ margin: "0 0 1.75rem" }} />

          {/* Duration */}
          <div style={{ marginBottom: "2rem" }}>
            <p className="label" style={{ marginBottom: "0.75rem" }}>Duration</p>
            <div className="toggle-group">
              <button
                type="button"
                id="duration-15"
                className={`toggle-btn ${duration === 15 ? "selected" : ""}`}
                onClick={() => setDuration(15)}
                disabled={loading}
              >
                ⏱️ 15 seconds
              </button>
              <button
                type="button"
                id="duration-30"
                className={`toggle-btn ${duration === 30 ? "selected" : ""}`}
                onClick={() => setDuration(30)}
                disabled={loading}
              >
                ⏱️ 30 seconds
              </button>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="error-box" style={{ marginBottom: "1.5rem" }} id="error-msg">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            id="generate-submit-btn"
            className="btn btn-primary"
            disabled={loading}
            style={{ width: "100%", justifyContent: "center", padding: "0.95rem" }}
          >
            {loading ? (
              <><span className="spinner" /> Generating ad…</>
            ) : (
              "🎬 Generate Video Ad"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
