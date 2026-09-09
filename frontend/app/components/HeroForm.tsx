"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

const URL_PATTERN = /^(https?:\/\/)?([\w-]+\.)+[a-z]{2,}(\/.*)?$/i;

export default function HeroForm() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const value = url.trim();

    if (!value) {
      setError("Enter your website URL to get started.");
      return;
    }
    if (!URL_PATTERN.test(value)) {
      setError("That doesn't look like a valid URL. Try something like stripe.com");
      return;
    }

    setError("");
    router.push(`/generate?url=${encodeURIComponent(value)}`);
  }

  return (
    <>
      <div className="hero-card">
        <div className="hero-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected="true"
            className="hero-tab selected"
          >
            Via URL
          </button>
          <button
            type="button"
            role="tab"
            aria-selected="false"
            className="hero-tab"
            disabled
            title="Coming soon — a URL is required for now"
          >
            Via business name
            <span className="badge badge-glass" style={{ marginLeft: "0.35rem", fontSize: "0.62rem", padding: "0.1rem 0.35rem" }}>
              Soon
            </span>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="hero-input-row" id="hero-generate-form">
          <input
            id="hero-url-input"
            className="input"
            type="text"
            placeholder="yourbusiness.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            aria-label="Business website URL"
          />
          <button type="submit" className="btn btn-primary btn-lg" id="hero-submit-btn">
            Create my ad
          </button>
        </form>

        {error && (
          <div className="error-box" style={{ marginTop: "0.85rem" }} id="hero-error">
            <span aria-hidden="true">⚠</span>
            <span>{error}</span>
          </div>
        )}
      </div>

      <div className="hero-bullets">
        <span className="hero-bullet"><span className="tick">✓</span> Video ready in under a minute</span>
        <span className="hero-bullet"><span className="tick">✓</span> 100% free, no signup</span>
        <span className="hero-bullet"><span className="tick">✓</span> Built from your real brand</span>
      </div>
    </>
  );
}
