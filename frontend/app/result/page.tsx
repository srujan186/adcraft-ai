"use client";
import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { videoFileUrl, type VideoResult, type AdScript } from "@/lib/api";
import { resultStore } from "@/lib/clientStore";
import BottomBanner from "./BottomBanner";
import VideoEditor from "./VideoEditor";

const SCRIPT_FIELDS: Array<{ key: keyof AdScript; label: string }> = [
  { key: "headline",          label: "Headline" },
  { key: "subtext",           label: "Subtext" },
  { key: "cta",               label: "Call to Action" },
  { key: "key_message",       label: "Key Message" },
  { key: "music_style",       label: "Music Style" },
  { key: "color_mood",        label: "Color Mood" },
  { key: "scene_description", label: "Scene Description" },
  { key: "voiceover",         label: "Voiceover Script" },
];

export default function ResultPage() {
  const router = useRouter();
  const [editing, setEditing] = useState(false);

  // Read from an external store rather than setState-in-effect, which React
  // flags as a cascading render.
  const raw = useSyncExternalStore(
    resultStore.subscribe,
    resultStore.getSnapshot,
    resultStore.getServerSnapshot
  );

  const result = useMemo<VideoResult | null>(() => {
    if (!raw) return null;
    try {
      return JSON.parse(raw) as VideoResult;
    } catch {
      return null;
    }
  }, [raw]);

  const videoSrc = result ? videoFileUrl(result.video_url) : "";

  // Nothing to show: send them back to the generator.
  //
  // Read the store directly rather than trusting `raw` here. During hydration
  // useSyncExternalStore returns the SERVER snapshot (always null), so keying
  // the redirect off `raw` bounced people away from a perfectly good result
  // before the client snapshot was ever applied. This effect runs after mount,
  // where getSnapshot() reflects real sessionStorage.
  useEffect(() => {
    if (resultStore.getSnapshot() === null) router.replace("/generate");
  }, [router]);

  if (!result) {
    return (
      <div style={{ textAlign: "center", padding: "6rem 0", color: "var(--text-muted)" }}>
        <span className="spinner spinner-dark" style={{ margin: "0 auto 1rem", display: "block" }} />
        <p>Loading result…</p>
      </div>
    );
  }

  const script = result.script;
  const scraped = result.scraped;

  if (editing) {
    return (
      <VideoEditor
        result={result}
        videoSrc={videoSrc}
        onBack={() => setEditing(false)}
      />
    );
  }

  function handleDownload() {
    const a = document.createElement("a");
    a.href = videoSrc;
    a.download = `adcraft_${scraped.business_name.replace(/\s+/g, "_")}.mp4`;
    a.click();
  }

  return (
    <section className="section">
      <div className="container" style={{ maxWidth: 900 }}>
        {/* Header */}
        <div style={{ marginBottom: "2rem" }}>
          <span className="badge" style={{ marginBottom: "0.85rem" }}>
            ✅ Your ad is ready
          </span>
          <h1 className="h2">{scraped.business_name} — Video Ad</h1>
          <p className="lead" style={{ marginTop: "0.5rem" }}>
            Download your video, tweak it in the editor, or create another one.
          </p>
        </div>

        {/* Video player */}
        <div className="video-wrap" style={{ marginBottom: "1.5rem" }} id="video-player">
          <video
            controls
            autoPlay
            src={videoSrc}
            onError={() => console.warn("Video load error – check backend /api/output route")}
          />
        </div>

        {/* Actions */}
        <div style={{ display: "flex", gap: "0.75rem", marginBottom: "2.5rem", flexWrap: "wrap" }}>
          <button id="download-btn" className="btn btn-primary" onClick={handleDownload}>
            ⬇️ Download MP4
          </button>
          <button
            id="edit-video-btn"
            className="btn btn-secondary"
            onClick={() => setEditing(true)}
          >
            ✏️ Edit video
          </button>
          <Link href="/generate" className="btn btn-secondary" id="create-another-btn">
            🔄 Create another
          </Link>
        </div>

        {/* Bottom banner editor */}
        {scraped && <BottomBanner scraped={scraped} />}

        {/* Brand info */}
        {scraped && (
          <div style={{ margin: "2.5rem 0" }}>
            <h2 className="h3" style={{ marginBottom: "1rem" }}>Brand extracted</h2>
            <div className="card" style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              <p><strong>Business:</strong> {scraped.business_name}</p>
              {scraped.tagline && <p><strong>Tagline:</strong> {scraped.tagline}</p>}
              {scraped.description && (
                <p className="feature-desc">{scraped.description}</p>
              )}
              {scraped.colors && (
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginTop: "0.3rem" }}>
                  <span className="hint">Colours detected:</span>
                  {Object.entries(scraped.colors).map(([k, v]) => (
                    <span
                      key={k}
                      title={`${k}: ${v}`}
                      style={{
                        display: "inline-block",
                        width: 22, height: 22,
                        borderRadius: "50%",
                        background: v,
                        border: "1px solid var(--border-str)",
                      }}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Ad script */}
        {script && (
          <div>
            <h2 className="h3" style={{ marginBottom: "1rem" }}>Generated script</h2>
            <div className="script-grid">
              {SCRIPT_FIELDS.map(({ key, label }) =>
                script[key] ? (
                  <div
                    key={key}
                    className="script-item"
                    style={key === "voiceover" || key === "scene_description" ? { gridColumn: "1 / -1" } : {}}
                  >
                    <p className="script-key">{label}</p>
                    <p className="script-val">{script[key]}</p>
                  </div>
                ) : null
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
