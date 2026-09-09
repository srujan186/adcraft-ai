"use client";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

// The four stages the pipeline actually moves through, in order. `step` is the
// index currently running; anything below it has finished.
const STAGES = [
  { label: "Reading your site" },
  { label: "Writing the script" },
  { label: "Recording the voiceover" },
  { label: "Scoring and rendering" },
];

// Shown one at a time on the white card while the render runs. Every claim
// here is a real property of the pipeline — see ../../CLAUDE.md.
const SLIDES = [
  {
    title: "Your site, read line by line",
    body: "We pull your logo, colours, tagline and copy straight off the page you gave us. Nothing to upload.",
  },
  {
    title: "A script written to length",
    body: "Llama 3.3 70B drafts the voiceover for the exact duration you picked, in the tone you chose.",
  },
  {
    title: "Narration generated locally",
    body: "Kokoro synthesises the voice on our own machine, so there is no third-party TTS queue between you and the render.",
  },
  {
    title: "Scored, mixed and rendered",
    body: "A licensed bed is mixed under the voice, then FFmpeg renders a 720p MP4 you can download and keep.",
  },
];

const SLIDE_MS = 5000;

export default function GeneratingOverlay({
  step,
  onCancel,
}: {
  step: number;
  onCancel: () => void;
}) {
  const [slide, setSlide] = useState(0);

  // Rotate the card, lock body scroll, and let Escape cancel.
  useEffect(() => {
    const timer = setInterval(
      () => setSlide((s) => (s + 1) % SLIDES.length),
      SLIDE_MS
    );

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", onKey);

    return () => {
      clearInterval(timer);
      document.body.style.overflow = prevOverflow;
      document.removeEventListener("keydown", onKey);
    };
  }, [onCancel]);

  const current = SLIDES[slide];

  return createPortal(
    <div
      className="gen-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Generating your ad"
    >
      <div className="gen-bar">
        <span className="brand" aria-hidden="true">
          <span className="brand-mark">⚡</span>
          AdCraft Studio
        </span>
        <button
          type="button"
          className="gen-close"
          onClick={onCancel}
          aria-label="Cancel generation"
          autoFocus
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
               strokeLinecap="round" aria-hidden="true">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="gen-body">
        <div className="gen-copy">
          <p className="gen-line">We&apos;re building your ad.</p>
          <p className="gen-line">It should take under a minute.</p>
          <p className="gen-line">In the meantime, here&apos;s what&apos;s happening.</p>
          <p className="gen-sign">— The AdCraft team</p>

          <ol className="gen-steps" aria-live="polite">
            {STAGES.map((stage, i) => (
              <li
                key={stage.label}
                className={`gen-step${step === i ? " active" : step > i ? " done" : ""}`}
              >
                <span className="gen-dot" aria-hidden="true">
                  {step > i ? "✓" : i + 1}
                </span>
                {stage.label}
                {step === i && <span className="visually-hidden"> — in progress</span>}
                {step > i && <span className="visually-hidden"> — done</span>}
              </li>
            ))}
          </ol>
        </div>

        <div className="gen-card">
          {/* Keyed so each slide re-runs its entry animation */}
          <div className="gen-slide" key={slide}>
            <p className="gen-slide-title">{current.title}</p>
            <p className="gen-slide-body">{current.body}</p>
          </div>

          <div className="gen-dots" aria-hidden="true">
            {SLIDES.map((s, i) => (
              <span key={s.title} className={`gen-pip${i === slide ? " on" : ""}`} />
            ))}
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
