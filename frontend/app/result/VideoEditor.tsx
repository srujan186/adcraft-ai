"use client";
import { useState, useRef } from "react";
import "./editor.css";
import type { VideoResult } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Edits {
  headline: string;
  subtext: string;
  cta: string;
  voiceover: string;
  musicStyle: string;
  primaryColor: string;
  accentColor: string;
  banner: {
    companyName: string;
    phone: string;
    address: string;
    website: string;
  };
}

type TabId = "text" | "voiceover" | "music" | "colors" | "banner";

const TABS: { id: TabId; icon: string; label: string }[] = [
  { id: "text",      icon: "📝", label: "Text" },
  { id: "voiceover", icon: "🎤", label: "Voice" },
  { id: "music",     icon: "🎵", label: "Music" },
  { id: "colors",    icon: "🎨", label: "Colors" },
  { id: "banner",    icon: "🏷️", label: "Banner" },
];

const MUSIC_OPTIONS = [
  { id: "upbeat",       icon: "⚡", name: "Upbeat",       desc: "Energetic & fast" },
  { id: "cinematic",    icon: "🎬", name: "Cinematic",    desc: "Epic orchestral" },
  { id: "corporate",    icon: "💼", name: "Corporate",    desc: "Clean & professional" },
  { id: "chill",        icon: "🌊", name: "Chill",        desc: "Relaxed & ambient" },
  { id: "inspirational",icon: "✨", name: "Inspire",      desc: "Motivational" },
  { id: "playful",      icon: "🎠", name: "Playful",      desc: "Fun & quirky" },
];

// ─── Component ────────────────────────────────────────────────────────────────

interface Props {
  result: VideoResult;
  videoSrc: string;
  onBack: () => void;
}

export default function VideoEditor({ result, videoSrc, onBack }: Props) {
  const { script, scraped } = result;
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>("text");
  const [saved, setSaved] = useState(false);
  const [globalSaved, setGlobalSaved] = useState(false);

  const [edits, setEdits] = useState<Edits>({
    headline:     script.headline,
    subtext:      script.subtext,
    cta:          script.cta,
    voiceover:    script.voiceover,
    musicStyle:   script.music_style,
    primaryColor: scraped.colors?.primary  ?? "#1a1a2e",
    accentColor:  scraped.colors?.accent   ?? "#6c63ff",
    banner: {
      companyName: scraped.business_name ?? "",
      phone:       "",
      address:     "",
      website:     "",
    },
  });

  // ── Helpers ────────────────────────────────────────────────────────────────

  function set<K extends keyof Edits>(key: K, value: Edits[K]) {
    setSaved(false);
    setEdits((e) => ({ ...e, [key]: value }));
  }

  function setBanner(field: keyof Edits["banner"], value: string) {
    setSaved(false);
    setEdits((e) => ({ ...e, banner: { ...e.banner, [field]: value } }));
  }

  function handleApply() {
    sessionStorage.setItem("adcraft_edits", JSON.stringify(edits));
    setSaved(true);
    setTimeout(() => setSaved(false), 2200);
  }

  function handleSaveExport() {
    sessionStorage.setItem("adcraft_edits", JSON.stringify(edits));
    setGlobalSaved(true);
    setTimeout(() => setGlobalSaved(false), 2500);
  }

  function togglePlay() {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) { v.play(); setPlaying(true); }
    else          { v.pause(); setPlaying(false); }
  }

  // ── Panel content ──────────────────────────────────────────────────────────

  function renderPanel() {
    switch (activeTab) {
      case "text": return (
        <>
          <div className="ve-panel-header">
            <div className="ve-panel-title">✏️ Edit Text</div>
            <div className="ve-panel-sub">Change headline, subtext and CTA</div>
          </div>
          <div className="ve-panel-body">
            <VeField label="Headline" id="ve-headline">
              <input className="ve-input" value={edits.headline}
                onChange={(e) => set("headline", e.target.value)} />
            </VeField>
            <VeField label="Subtext" id="ve-subtext">
              <textarea className="ve-textarea" value={edits.subtext}
                onChange={(e) => set("subtext", e.target.value)} />
            </VeField>
            <VeField label="Call to Action" id="ve-cta">
              <input className="ve-input" value={edits.cta}
                onChange={(e) => set("cta", e.target.value)} />
            </VeField>
          </div>
        </>
      );

      case "voiceover": return (
        <>
          <div className="ve-panel-header">
            <div className="ve-panel-title">🎤 Voiceover Script</div>
            <div className="ve-panel-sub">Edit the narration script</div>
          </div>
          <div className="ve-panel-body">
            <VeField label="Script" id="ve-voiceover">
              <textarea className="ve-textarea"
                style={{ minHeight: 160 }}
                value={edits.voiceover}
                onChange={(e) => set("voiceover", e.target.value)} />
            </VeField>
            <p style={{ fontSize: "0.72rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
              Keep it under {script.voiceover?.split(" ").length ?? 60} words to match your video duration.
            </p>
          </div>
        </>
      );

      case "music": return (
        <>
          <div className="ve-panel-header">
            <div className="ve-panel-title">🎵 Music Style</div>
            <div className="ve-panel-sub">Choose background music mood</div>
          </div>
          <div className="ve-panel-body">
            <div className="ve-music-grid">
              {MUSIC_OPTIONS.map((m) => (
                <button
                  key={m.id}
                  id={`ve-music-${m.id}`}
                  onClick={() => set("musicStyle", m.id)}
                  className={`ve-music-chip${edits.musicStyle === m.id ? " selected" : ""}`}
                >
                  <span className="ve-chip-icon">{m.icon}</span>
                  <span className="ve-chip-name">{m.name}</span>
                  <span className="ve-chip-desc">{m.desc}</span>
                </button>
              ))}
            </div>
          </div>
        </>
      );

      case "colors": return (
        <>
          <div className="ve-panel-header">
            <div className="ve-panel-title">🎨 Brand Colors</div>
            <div className="ve-panel-sub">Adjust the color palette</div>
          </div>
          <div className="ve-panel-body">
            <VeField label="Primary Color" id="ve-primary-color">
              <div className="ve-color-row">
                <div className="ve-color-swatch">
                  <input type="color" id="ve-color-primary"
                    value={edits.primaryColor}
                    onChange={(e) => set("primaryColor", e.target.value)} />
                </div>
                <span className="ve-color-val">{edits.primaryColor}</span>
              </div>
            </VeField>
            <VeField label="Accent Color" id="ve-accent-color">
              <div className="ve-color-row">
                <div className="ve-color-swatch">
                  <input type="color" id="ve-color-accent"
                    value={edits.accentColor}
                    onChange={(e) => set("accentColor", e.target.value)} />
                </div>
                <span className="ve-color-val">{edits.accentColor}</span>
              </div>
            </VeField>
            {/* Color preview swatches */}
            <div style={{ marginTop: "0.5rem" }}>
              <div className="ve-label" style={{ marginBottom: "0.5rem" }}>Preview</div>
              <div style={{ display: "flex", gap: "0.5rem", height: 48, borderRadius: 8, overflow: "hidden" }}>
                <div style={{ flex: 1, background: edits.primaryColor, borderRadius: "6px 0 0 6px" }} />
                <div style={{ flex: 1, background: edits.accentColor,  borderRadius: "0 6px 6px 0" }} />
              </div>
            </div>
          </div>
        </>
      );

      case "banner": return (
        <>
          <div className="ve-panel-header">
            <div className="ve-panel-title">🏷️ Bottom Banner</div>
            <div className="ve-panel-sub">Company info shown at the bottom</div>
          </div>
          <div className="ve-panel-body">
            <VeField label="Company Name" id="ve-banner-company">
              <input className="ve-input" value={edits.banner.companyName}
                placeholder="Nike, Inc."
                onChange={(e) => setBanner("companyName", e.target.value)} />
            </VeField>
            <VeField label="Phone Number" id="ve-banner-phone">
              <input className="ve-input" value={edits.banner.phone}
                placeholder="+1 (800) 555-0100"
                onChange={(e) => setBanner("phone", e.target.value)} />
            </VeField>
            <VeField label="Address" id="ve-banner-address">
              <input className="ve-input" value={edits.banner.address}
                placeholder="One Bowerman Drive, OR"
                onChange={(e) => setBanner("address", e.target.value)} />
            </VeField>
            <VeField label="Website" id="ve-banner-website">
              <input className="ve-input" value={edits.banner.website}
                placeholder="nike.com"
                onChange={(e) => setBanner("website", e.target.value)} />
            </VeField>
          </div>
        </>
      );
    }
  }

  const showBanner = activeTab === "banner" && (
    edits.banner.companyName || edits.banner.phone || edits.banner.address || edits.banner.website
  );

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="ve-shell">

      {/* ── Top bar ─────────────────────────────────── */}
      <div className="ve-topbar">
        <div className="ve-topbar-left">
          <button id="ve-back-btn" className="ve-back-btn" onClick={onBack}>
            ← Back
          </button>
          <span className="ve-title">✏️ Video Editor — {scraped.business_name}</span>
        </div>
        <div className="ve-topbar-right">
          <button
            id="ve-save-export-btn"
            className="ve-save-btn"
            onClick={handleSaveExport}
          >
            {globalSaved ? "✅ Saved!" : "💾 Save & Export"}
          </button>
        </div>
      </div>

      {/* ── Body ────────────────────────────────────── */}
      <div className="ve-body">

        {/* Icon sidebar */}
        <div className="ve-icon-sidebar">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              id={`ve-tab-${tab.id}`}
              className={`ve-icon-btn${activeTab === tab.id ? " active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
              title={tab.label}
            >
              <span>{tab.icon}</span>
              <span className="ve-icon-label">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Edit panel */}
        <div className="ve-edit-panel">
          {renderPanel()}
          <div className="ve-panel-save">
            <button
              id="ve-apply-btn"
              className={`ve-apply-btn${saved ? " saved" : ""}`}
              onClick={handleApply}
            >
              {saved ? "✅ Applied!" : "✔ Apply Changes"}
            </button>
          </div>
        </div>

        {/* Main — video + timeline */}
        <div className="ve-main">
          {/* Video preview */}
          <div className="ve-video-area">
            <div className="ve-video-wrap">
              <video
                ref={videoRef}
                src={videoSrc}
                controls={false}
                onEnded={() => setPlaying(false)}
                style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
              />
              {/* Live banner preview overlay */}
              {showBanner && (
                <div
                  className="ve-banner-overlay"
                  style={{ background: edits.primaryColor }}
                >
                  <span className="ve-banner-company">
                    {edits.banner.companyName}
                  </span>
                  <div className="ve-banner-contacts">
                    {edits.banner.phone   && <span>📞 {edits.banner.phone}</span>}
                    {edits.banner.address && <span>📍 {edits.banner.address}</span>}
                  </div>
                  {edits.banner.website && (
                    <span
                      className="ve-banner-pill"
                      style={{ background: edits.accentColor }}
                    >
                      {edits.banner.website}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Timeline */}
          <div className="ve-timeline">
            <div className="ve-tl-controls">
              <button id="ve-play-btn" className="ve-play-btn" onClick={togglePlay}>
                {playing ? "⏸" : "▶"}
              </button>
              <span className="ve-duration-badge">
                {result.script ? "0:00" : "--:--"}
              </span>
              <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginLeft: "0.5rem" }}>
                Timeline (visual)
              </span>
            </div>
            <div className="ve-tracks">
              {[
                { label: "BOTTOM BANNER", color: "#ec4899", width: "65%" },
                { label: "MUSIC",         color: "#14b8a6", width: "100%" },
                { label: "VOICE & SCRIPT",color: "#8b5cf6", width: "88%" },
                { label: "VIDEO CLIPS",   color: "#3b82f6", width: "100%" },
              ].map((track) => (
                <div key={track.label} className="ve-track">
                  <span className="ve-track-label">{track.label}</span>
                  <div
                    className="ve-track-bar"
                    style={{ background: track.color, width: track.width }}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Small helper ─────────────────────────────────────────────────────────────
function VeField({
  label, id, children,
}: {
  label: string; id: string; children: React.ReactNode;
}) {
  return (
    <div className="ve-field">
      <label htmlFor={id} className="ve-label">{label}</label>
      {children}
    </div>
  );
}
