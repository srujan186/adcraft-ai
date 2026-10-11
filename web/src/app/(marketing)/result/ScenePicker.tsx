"use client";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { portalRoot } from "../components/portalRoot";
import { searchPhotos, type StockPhoto } from "@/lib/legacy/api";
import type { SceneOverride } from "@/lib/legacy/clientStore";

/**
 * Downscale an uploaded image before it becomes a data URL.
 *
 * A phone photo is several MB; base64 inflates that by a third, and
 * sessionStorage caps out around 5MB. Without this the override would be
 * silently dropped on write and vanish on reload.
 */
async function fileToDataUrl(file: File, maxWidth = 960): Promise<string> {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, maxWidth / bitmap.width);
  const w = Math.round(bitmap.width * scale);
  const h = Math.round(bitmap.height * scale);

  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas unavailable");
  ctx.drawImage(bitmap, 0, 0, w, h);
  bitmap.close();

  return canvas.toDataURL("image/jpeg", 0.82);
}

export default function ScenePicker({
  sceneLabel,
  seedQuery,
  onPick,
  onClose,
}: {
  sceneLabel: string;
  seedQuery: string;
  onPick: (o: SceneOverride) => void;
  onClose: () => void;
}) {
  const [query, setQuery] = useState(seedQuery);
  const [photos, setPhotos] = useState<StockPhoto[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  // Close on Escape. No state is set synchronously here, so the React
  // Compiler's set-state-in-effect rule stays satisfied.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  async function runSearch(e?: React.FormEvent) {
    e?.preventDefault();
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError("");
    try {
      setPhotos(await searchPhotos(q));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Image search failed.");
      setPhotos([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("That file isn't an image.");
      return;
    }
    setError("");
    try {
      onPick({ src: await fileToDataUrl(file), kind: "upload" });
    } catch {
      setError("We couldn't read that image. Try a different file.");
    }
  }

  return createPortal(
    <div className="sp-scrim" onClick={onClose} role="presentation">
      <div
        className="sp-modal"
        role="dialog"
        aria-modal="true"
        aria-label={`Replace ${sceneLabel}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sp-head">
          <div>
            <p className="sp-title">Replace {sceneLabel}</p>
            <p className="sp-sub">Upload your own image, or search free stock photos.</p>
          </div>
          <button className="sp-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <div className="sp-upload">
          <button className="sp-upload-btn" onClick={() => fileRef.current?.click()}>
            Upload an image
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            hidden
            onChange={handleFile}
          />
          <span className="sp-upload-hint">JPG or PNG, resized to 960px wide</span>
        </div>

        <form className="sp-search" onSubmit={runSearch}>
          <input
            className="sp-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search stock photos…"
            aria-label="Search stock photos"
          />
          <button className="sp-search-btn" type="submit" disabled={loading}>
            {loading ? "Searching…" : "Search"}
          </button>
        </form>

        {error && <p className="sp-error">{error}</p>}

        <div className="sp-results">
          {photos.length === 0 && !loading && !error && (
            <p className="sp-empty">
              Search for something that fits this scene — a product, a place, a mood.
            </p>
          )}
          {photos.map((p) => (
            <button
              key={p.id}
              className="sp-thumb"
              onClick={() =>
                onPick({
                  src: p.full,
                  kind: "stock",
                  credit: p.author,
                  creditUrl: p.author_url,
                })
              }
              title={p.alt}
            >
              {/* Pexels CDN is not in next.config's image allowlist, and these
                  are transient search results — a plain <img> is correct. */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={p.thumb} alt={p.alt} loading="lazy" />
              <span className="sp-credit">{p.author}</span>
            </button>
          ))}
        </div>

        <p className="sp-footnote">
          Stock photos by{" "}
          <a href="https://www.pexels.com" target="_blank" rel="noreferrer noopener">
            Pexels
          </a>
          . Your choice is saved with this ad, but the downloaded MP4 still
          shows the original render — re-rendering isn&apos;t wired up yet.
        </p>
      </div>
    </div>,
    portalRoot()
  );
}
