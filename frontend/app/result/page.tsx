"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { videoFileUrl, type VideoResult, type AdScript } from "@/lib/api";
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
  const [result, setResult] = useState<VideoResult | null>(null);
  const [videoSrc, setVideoSrc] = useState("");
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    const raw = sessionStorage.getItem("adcraft_result");
    if (!raw) { router.replace("/generate"); return; }
    const data: VideoResult = JSON.parse(raw);
    setResult(data);
    // video_url may be a filename or a relative path
    setVideoSrc(videoFileUrl(data.video_url));
  }, [router]);

  if (!result) {
    return (
      <div style={{ textAlign: "center", padding: "6rem 0", color: "var(--text-muted)" }}>
        <div className="spinner" style={{ margin: "0 auto 1rem" }} />
        <p>Loading result…</p>
      </div>
    );
  }

  const script = result.script;
  const scraped = result.scraped;

  // ── Show the full-screen editor ─────────────────────────────────────────
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
    <div className="section" style={{ padding: "3rem 0 5rem" }}>
      <div className="container" style={{ maxWidth: 820 }}>
        {/* Header */}
        <div className="fade-up" style={{ marginBottom: "2rem" }}>
          <div className="badge" style={{ marginBottom: "0.75rem" }}>✅ Your ad is ready</div>
          <h1 className="section-title">
            {scraped.business_name} — Video Ad
          </h1>
          <p className="section-sub">
            Download your video or create another one below.
          </p>
        </div>

        {/* Video player */}
        <div className="video-wrap fade-up fade-up-d1" style={{ marginBottom: "1.5rem" }} id="video-player">
          <video
            controls
            autoPlay
            src={videoSrc}
            onError={() => console.warn("Video load error – check backend /api/output route")}
          />
        </div>

        {/* Action buttons */}
        <div style={{ display: "flex", gap: "0.75rem", marginBottom: "2.5rem" }} className="fade-up fade-up-d2">
          <button
            id="download-btn"
            className="btn btn-primary"
            onClick={handleDownload}
          >
            ⬇️ Download MP4
          </button>
          <button
            id="edit-video-btn"
            className="btn btn-secondary"
            onClick={() => setEditing(true)}
            style={{ borderColor: "rgba(108,99,255,0.4)", color: "var(--accent2)" }}
          >
            ✏️ Edit Video
          </button>
          <Link href="/generate" className="btn btn-secondary" id="create-another-btn">
            🔄 Create Another
          </Link>
        </div>

        <div className="divider" />

        {/* ── Bottom Banner editor ──────────────────────────────── */}
        {scraped && <BottomBanner scraped={scraped} />}

        <div className="divider" style={{ marginTop: "2rem" }} />

        {/* Brand info */}
        {scraped && (
          <div className="fade-up" style={{ margin: "2rem 0" }}>
            <h2 className="section-title" style={{ fontSize: "1.2rem", marginBottom: "1rem" }}>
              Brand Extracted
            </h2>
            <div className="card" style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              <p><strong>Business:</strong> {scraped.business_name}</p>
              {scraped.tagline && <p><strong>Tagline:</strong> {scraped.tagline}</p>}
              {scraped.description && (
                <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>{scraped.description}</p>
              )}
              {scraped.colors && (
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginTop: "0.3rem" }}>
                  <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Colors detected:</span>
                  {Object.entries(scraped.colors).map(([k, v]) => (
                    <span
                      key={k}
                      title={`${k}: ${v}`}
                      style={{
                        display: "inline-block",
                        width: 20, height: 20,
                        borderRadius: "50%",
                        background: v,
                        border: "1px solid rgba(255,255,255,0.15)",
                      }}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Ad Script */}
        {script && (
          <div className="fade-up fade-up-d1">
            <h2 className="section-title" style={{ fontSize: "1.2rem", marginBottom: "1rem" }}>
              Generated Script
            </h2>
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
    </div>
  );
}
