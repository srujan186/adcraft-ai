"use client";
import { useCallback, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { generateVideo, type AdStyle } from "@/lib/legacy/api";
import { resetEditorState, resultStore } from "@/lib/legacy/clientStore";
import GeneratingOverlay from "./GeneratingOverlay";

const STYLES: { key: AdStyle; name: string; emoji: string; desc: string }[] = [
  { key: "modern",  name: "Modern",  emoji: "✨", desc: "Clean, professional, confident" },
  { key: "bold",    name: "Bold",    emoji: "⚡", desc: "High energy, punchy, exciting" },
  { key: "minimal", name: "Minimal", emoji: "◻️", desc: "Simple, elegant, one big idea" },
  { key: "playful", name: "Playful", emoji: "🎉", desc: "Fun, friendly, approachable" },
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
  const abortRef = useRef<AbortController | null>(null);

  // Only closes over the ref and setters, so the React Compiler's
  // preserve-manual-memoization rule stays happy.
  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setLoading(false);
    setStep(-1);
    setError("");
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const value = url.trim();

    if (!value) { setError("Please enter a URL"); return; }
    if (!URL_PATTERN.test(value)) {
      setError("That doesn't look like a valid URL. Try something like yourbusiness.com");
      return;
    }

    setError("");
    setLoading(true);

    const controller = new AbortController();
    abortRef.current = controller;

    setStep(0);
    const stepTimer1 = setTimeout(() => setStep(1), 8000);
    const stepTimer2 = setTimeout(() => setStep(2), 20000);
    const stepTimer3 = setTimeout(() => setStep(3), 32000);

    try {
      const result = await generateVideo(value, style, duration, controller.signal);
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      clearTimeout(stepTimer3);
      // Drop the previous ad's scene uploads and banner before the new
      // result lands, or they bleed into an unrelated brand's video.
      resetEditorState();
      // Write THROUGH the store, not sessionStorage directly: the store keeps a
      // module-level cache and getSnapshot returns it, so a raw setItem left the
      // result page serving the previous ad until a full reload. This updates
      // the cache and notifies the page immediately.
      resultStore.write(result);
      router.push("/result");
    } catch (err: unknown) {
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      clearTimeout(stepTimer3);
      setStep(-1);

      // Cancelling is a deliberate act, not a failure — say nothing.
      if (controller.signal.aborted) return;

      // The backend already explains what went wrong and what to try next —
      // it can tell a DNS failure from a timeout from a block. This used to
      // overwrite all of that with one generic line whenever the text merely
      // contained "url", which threw away the only useful part.
      const errorMessage =
        err instanceof Error && err.message
          ? err.message
          : "Something went wrong. Please try again.";

      setError(errorMessage);
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
      setLoading(false);
    }
  }

  return (
    <>
      {/* Full-screen while the render runs — the form stays mounted beneath so
          the chosen settings survive a cancel. */}
      {loading && <GeneratingOverlay step={step} onCancel={cancel} />}

      <form onSubmit={handleSubmit} className="card card-pad-lg" id="generate-form">
        {/* URL input */}
        <div className="input-wrap" style={{ marginBottom: "1.75rem" }}>
          <label htmlFor="url-input" className="label">Business URL</label>
          <input
            id="url-input"
            className="input"
            type="text"
            placeholder="e.g. yourbusiness.com or https://yourbusiness.com"
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
            "Generate video ad"
          )}
        </button>
      </form>
    </>
  );
}
