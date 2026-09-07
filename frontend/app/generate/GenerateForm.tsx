"use client";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
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

const URL_PATTERN = /^(https?:\/\/)?([\w-]+\.)+[a-z]{2,}(\/.*)?$/i;

export default function GenerateForm() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [url, setUrl] = useState(searchParams.get("url") ?? "");
  const [style, setStyle] = useState<AdStyle>("modern");
  const [duration, setDuration] = useState<15 | 30>(15);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(-1);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const value = url.trim();

    if (!value) { setError("Please enter a URL"); return; }
    if (!URL_PATTERN.test(value)) {
      setError("That doesn't look like a valid URL. Try something like stripe.com");
      return;
    }

    setError("");
    setLoading(true);

    setStep(0);
    const stepTimer1 = setTimeout(() => setStep(1), 8000);
    const stepTimer2 = setTimeout(() => setStep(2), 20000);

    try {
      const result = await generateVideo(value, style, duration);
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      setStep(3);
      sessionStorage.setItem("adcraft_result", JSON.stringify(result));
      router.push("/result");
    } catch (err: unknown) {
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      setStep(-1);

      let errorMessage =
        err instanceof Error ? err.message : "Something went wrong. Please try again.";
      if (
        errorMessage.includes("couldn't automatically read") ||
        errorMessage.includes("Could not scrape") ||
        errorMessage.toLowerCase().includes("url")
      ) {
        errorMessage = "We couldn't read that URL. Please check it and try again.";
      }

      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {/* Progress stepper — visible while loading */}
      {loading && (
        <div className="card" style={{ marginBottom: "1.5rem" }} id="progress-stepper">
          <p
            style={{
              fontSize: "0.85rem",
              color: "var(--text-muted)",
              marginBottom: "1.5rem",
              textAlign: "center",
            }}
          >
            Generating your ad — this usually takes 30–60 seconds
          </p>
          <div className="stepper">
            {STEPS.map((s, i) => (
              <div
                key={s.label}
                className={`step ${step === i ? "active" : step > i ? "done" : ""}`}
              >
                <div className="step-icon">{step > i ? "✓" : s.icon}</div>
                <span className="step-label">{s.label}</span>
                {i < STEPS.length - 1 && <div className="step-line" />}
              </div>
            ))}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="card card-pad-lg" id="generate-form">
        {/* URL input */}
        <div className="input-wrap" style={{ marginBottom: "1.75rem" }}>
          <label htmlFor="url-input" className="label">Business URL</label>
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
          <span className="hint">
            We&apos;ll screenshot your website and extract your logo, colours &amp; brand info.
          </span>
        </div>

        <div className="divider" style={{ margin: "0 0 1.75rem" }} />

        {/* Style picker */}
        <div style={{ marginBottom: "1.75rem" }}>
          <p className="label" style={{ marginBottom: "0.75rem" }}>Ad style</p>
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

        {error && (
          <div className="error-box" style={{ marginBottom: "1.5rem" }} id="error-msg">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        <button
          type="submit"
          id="generate-submit-btn"
          className="btn btn-primary btn-lg btn-block"
          disabled={loading}
        >
          {loading ? (
            <><span className="spinner" /> Generating ad…</>
          ) : (
            "🎬 Generate video ad"
          )}
        </button>
      </form>
    </>
  );
}
