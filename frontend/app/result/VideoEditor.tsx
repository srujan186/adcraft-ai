"use client";
import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import "./editor.css";
import { rerenderVideo, type VideoResult } from "@/lib/api";
import {
  bannerStore,
  resultStore,
  scenesStore,
  type BannerData,
  type SceneOverride,
  type SceneOverrides,
} from "@/lib/clientStore";
import ScenePicker from "./ScenePicker";

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

type TabId = "scenes" | "text" | "voiceover" | "music" | "colors" | "banner";

// The renderer builds the background from three screenshots of the site, so
// the ad always has exactly three scenes of equal length.
const SCENE_COUNT = 3;

const TABS: { id: TabId; icon: string; label: string }[] = [
  { id: "scenes",    icon: "🎞️", label: "Scenes" },
  { id: "text",      icon: "📝", label: "Text" },
  { id: "voiceover", icon: "🎤", label: "Voice" },
  { id: "music",     icon: "🎵", label: "Music" },
  { id: "colors",    icon: "🎨", label: "Colors" },
  { id: "banner",    icon: "🏷️", label: "Banner" },
];

// The ids must match STYLE_KEYWORDS in backend/services/music.py — the backend
// resolves them to one of the five beds in backend/music/. Offering ids the
// backend doesn't know ("cinematic", "chill", "playful") meant three of these
// could never resolve to the bed they named.
const MUSIC_OPTIONS = [
  { id: "upbeat",        icon: "⚡", name: "Upbeat",    desc: "Energetic & fast" },
  { id: "dramatic",      icon: "🎬", name: "Cinematic", desc: "Epic orchestral" },
  { id: "corporate",     icon: "💼", name: "Corporate", desc: "Clean & professional" },
  { id: "calm",          icon: "🌊", name: "Chill",     desc: "Relaxed & ambient" },
  { id: "inspirational", icon: "✨", name: "Inspire",   desc: "Motivational" },
];

/**
 * Pull one still per scene out of the rendered MP4.
 *
 * The backend never exposes the screenshots it captured (they live in temp/),
 * so the honest source for a scene thumbnail is the finished video itself.
 * Needs crossOrigin="anonymous" plus the CORS header the API already sends —
 * without it drawImage taints the canvas and toDataURL throws.
 */
function useSceneThumbs(src: string, count: number) {
  const [thumbs, setThumbs] = useState<string[]>([]);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    if (!src) return;
    let cancelled = false;

    const v = document.createElement("video");
    v.crossOrigin = "anonymous";
    v.preload = "auto";
    v.muted = true;

    const shots: string[] = [];
    let i = 0;

    const seekNext = () => {
      // Mid-point of each scene reads better than its first frame.
      v.currentTime = (v.duration / count) * (i + 0.5);
    };

    const onMeta = () => {
      if (cancelled) return;
      setDuration(v.duration);
      seekNext();
    };

    const onSeeked = () => {
      if (cancelled) return;
      const canvas = document.createElement("canvas");
      const ratio = v.videoHeight && v.videoWidth ? v.videoHeight / v.videoWidth : 0.5625;
      canvas.width = 320;
      canvas.height = Math.round(320 * ratio);
      const ctx = canvas.getContext("2d");
      try {
        ctx?.drawImage(v, 0, 0, canvas.width, canvas.height);
        shots.push(canvas.toDataURL("image/jpeg", 0.7));
      } catch {
        shots.push(""); // tainted canvas — fall back to a placeholder tile
      }
      i += 1;
      if (i < count) seekNext();
      else setThumbs(shots);
    };

    v.addEventListener("loadedmetadata", onMeta);
    v.addEventListener("seeked", onSeeked);
    v.src = src;

    return () => {
      cancelled = true;
      v.removeEventListener("loadedmetadata", onMeta);
      v.removeEventListener("seeked", onSeeked);
      v.src = "";
    };
  }, [src, count]);

  return { thumbs, duration };
}

function fmt(seconds: number) {
  if (!Number.isFinite(seconds)) return "0:00";
  const s = Math.floor(seconds);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

// ─── Component ────────────────────────────────────────────────────────────────

interface Props {
  result: VideoResult;
  videoSrc: string;
  /** Leaves the editor — the result page routes this to /generate. */
  onBack: () => void;
  onDownload: () => void;
}

export default function VideoEditor({ result, videoSrc, onBack, onDownload }: Props) {
  const { script, scraped } = result;
  const videoRef = useRef<HTMLVideoElement>(null);
  const lanesRef = useRef<HTMLDivElement>(null);
  const [playing, setPlaying] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>("scenes");
  const [pickerScene, setPickerScene] = useState<number | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [saved, setSaved] = useState(false);
  const [globalSaved, setGlobalSaved] = useState(false);
  const [rendering, setRendering] = useState(false);
  const [renderError, setRenderError] = useState("");

  // The banner lives in a store shared with the result page's Bottom Banner
  // panel, so the two stay in step instead of silently diverging.
  const bannerRaw = useSyncExternalStore(
    bannerStore.subscribe,
    bannerStore.getSnapshot,
    bannerStore.getServerSnapshot
  );

  const { thumbs, duration } = useSceneThumbs(videoSrc, SCENE_COUNT);

  const scenesRaw = useSyncExternalStore(
    scenesStore.subscribe,
    scenesStore.getSnapshot,
    scenesStore.getServerSnapshot
  );

  const sceneOverrides = useMemo<SceneOverrides>(() => {
    if (!scenesRaw) return {};
    try {
      return JSON.parse(scenesRaw) as SceneOverrides;
    } catch {
      return {};
    }
  }, [scenesRaw]);

  const storedBanner = useMemo<Partial<BannerData>>(() => {
    if (!bannerRaw) return {};
    try {
      return JSON.parse(bannerRaw) as Partial<BannerData>;
    } catch {
      return {};
    }
  }, [bannerRaw]);

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

  // Saved banner values take precedence over this component's initial state.
  const banner = { ...edits.banner, ...storedBanner };

  // ── Helpers ────────────────────────────────────────────────────────────────

  function set<K extends keyof Edits>(key: K, value: Edits[K]) {
    setSaved(false);
    setEdits((e) => ({ ...e, [key]: value }));
  }

  function setBanner(field: keyof Edits["banner"], value: string) {
    setSaved(false);
    const next = { ...banner, [field]: value };
    setEdits((e) => ({ ...e, banner: next }));
    // Publish immediately so the result page's panel reflects it.
    bannerStore.write({
      companyName:  next.companyName,
      phone:        next.phone,
      address:      next.address,
      website:      next.website,
      primaryColor: edits.primaryColor,
      accentColor:  edits.accentColor,
    });
  }

  function pickScene(index: number, override: SceneOverride) {
    scenesStore.write({ ...sceneOverrides, [String(index)]: override });
    setPickerScene(null);
    setSaved(false);
  }

  function clearScene(index: number) {
    const next = { ...sceneOverrides };
    delete next[String(index)];
    scenesStore.write(next);
    setSaved(false);
  }

  /** The image shown for a scene: the user's replacement, else the real frame. */
  function sceneImage(i: number): string {
    return sceneOverrides[String(i)]?.src || thumbs[i] || "";
  }

  function sceneRange(i: number): string {
    if (!duration) return "—";
    const per = duration / SCENE_COUNT;
    return `${fmt(per * i)} – ${fmt(per * (i + 1))}`;
  }

  // A tick each second, labelled every five. Keeps 15s and 30s ads legible
  // without crowding the ruler.
  const ticks = duration
    ? Array.from({ length: Math.floor(duration) + 1 }, (_, s) => ({
        at: s,
        major: s % 5 === 0,
      }))
    : [];

  const activeScene = duration
    ? Math.min(SCENE_COUNT - 1, Math.floor((currentTime / duration) * SCENE_COUNT))
    : 0;

  function handleApply() {
    sessionStorage.setItem("adcraft_edits", JSON.stringify(edits));
    setSaved(true);
    setTimeout(() => setSaved(false), 2200);
  }

  async function handleSaveExport() {
    sessionStorage.setItem("adcraft_edits", JSON.stringify(edits));
    setRenderError("");
    setRendering(true);

    try {
      // Only 15 and 30 exist, so the midpoint separates them safely.
      const secs = videoRef.current?.duration ?? duration;
      const adDuration: 15 | 30 = secs > 22 ? 30 : 15;

      const fresh = await rerenderVideo({
        business_name: scraped.business_name,
        duration: adDuration,
        url: scraped.url ?? "",
        logo_url: scraped.logo_url ?? "",
        colors: {
          primary: edits.primaryColor,
          secondary: scraped.colors?.secondary ?? "#ffffff",
          accent: edits.accentColor,
        },
        script: {
          headline: edits.headline,
          subtext: edits.subtext,
          cta: edits.cta,
          voiceover: edits.voiceover,
          music_style: edits.musicStyle,
          scene_description: script.scene_description ?? "",
        },
        // "" keeps the scene as-is; the backend re-shoots those from the site.
        scene_images: Array.from(
          { length: SCENE_COUNT },
          (_, i) => sceneOverrides[String(i)]?.src ?? ""
        ),
      });

      // Writing the store re-renders the page with the new file, which flows
      // back down as a fresh videoSrc. This component keeps its edit state.
      resultStore.write({ ...result, video_url: fresh.video_url, render_id: fresh.render_id });

      setGlobalSaved(true);
      setTimeout(() => setGlobalSaved(false), 2500);
    } catch (err) {
      setRenderError(
        err instanceof Error ? err.message : "Re-render failed. Please try again."
      );
    } finally {
      setRendering(false);
    }
  }

  /** Map a click anywhere in the lane area to a timecode. */
  function scrubTo(clientX: number) {
    const el = lanesRef.current;
    const v = videoRef.current;
    if (!el || !v || !duration) return;
    const rect = el.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    v.currentTime = ratio * duration;
    setCurrentTime(ratio * duration);
  }

  /** Jump the preview to the start of a scene. */
  function showScene(i: number) {
    const v = videoRef.current;
    if (!v || !duration) return;
    const at = (duration / SCENE_COUNT) * i;
    v.currentTime = at;
    setCurrentTime(at);
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
      case "scenes": return (
        <>
          <div className="ve-panel-header">
            <div className="ve-panel-title">Scenes</div>
            <div className="ve-panel-sub">
              Three shots of your site, split evenly across the ad
            </div>
          </div>
          <div className="ve-panel-body">
            <div className="ve-scene-list">
              {Array.from({ length: SCENE_COUNT }, (_, i) => {
                const override = sceneOverrides[String(i)];
                const img = sceneImage(i);
                return (
                  <div
                    key={i}
                    className={`ve-scene${activeScene === i ? " current" : ""}`}
                    role="button"
                    tabIndex={0}
                    aria-label={`Jump to scene ${i + 1}`}
                    onClick={() => showScene(i)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        showScene(i);
                      }
                    }}
                  >
                    <div className="ve-scene-thumb">
                      {img ? (
                        /* eslint-disable-next-line @next/next/no-img-element */
                        <img src={img} alt={`Scene ${i + 1}`} />
                      ) : (
                        <span className="ve-scene-empty">{i + 1}</span>
                      )}
                      <button
                        className="ve-scene-change"
                        /* Without this the row's own click handler also fires
                           and the preview jumps behind the open picker. */
                        onClick={(e) => {
                          e.stopPropagation();
                          setPickerScene(i);
                        }}
                        id={`ve-scene-change-${i}`}
                      >
                        Change
                      </button>
                    </div>
                    <div className="ve-scene-meta">
                      <p className="ve-scene-name">Scene #{i + 1}</p>
                      <p className="ve-scene-time">{sceneRange(i)}</p>
                      {activeScene === i && (
                        <p className="ve-scene-now">Currently visible</p>
                      )}
                      {override && (
                        <p className="ve-scene-swapped">
                          <span className="ve-scene-src">
                            {override.kind === "upload" ? "Your image" : `Stock · ${override.credit}`}
                          </span>
                          <button
                            className="ve-scene-reset"
                            onClick={(e) => {
                              e.stopPropagation();
                              clearScene(i);
                            }}
                          >
                            Reset
                          </button>
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      );

      case "text": return (
        <>
          <div className="ve-panel-header">
            <div className="ve-panel-title">✏️ Edit Text</div>
            <div className="ve-panel-sub">Change headline, subtext and CTA</div>
          </div>
          <div className="ve-panel-body">
            <VeField label="Headline" id="ve-headline">
              <input id="ve-headline" className="ve-input" value={edits.headline}
                onChange={(e) => set("headline", e.target.value)} />
            </VeField>
            <VeField label="Subtext" id="ve-subtext">
              <textarea id="ve-subtext" className="ve-textarea" value={edits.subtext}
                onChange={(e) => set("subtext", e.target.value)} />
            </VeField>
            <VeField label="Call to Action" id="ve-cta">
              <input id="ve-cta" className="ve-input" value={edits.cta}
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
              <textarea id="ve-voiceover" className="ve-textarea"
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
              <input id="ve-banner-company" className="ve-input" value={banner.companyName}
                placeholder="Nike, Inc."
                onChange={(e) => setBanner("companyName", e.target.value)} />
            </VeField>
            <VeField label="Phone Number" id="ve-banner-phone">
              <input id="ve-banner-phone" className="ve-input" value={banner.phone}
                placeholder="+1 (800) 555-0100"
                onChange={(e) => setBanner("phone", e.target.value)} />
            </VeField>
            <VeField label="Address" id="ve-banner-address">
              <input id="ve-banner-address" className="ve-input" value={banner.address}
                placeholder="One Bowerman Drive, OR"
                onChange={(e) => setBanner("address", e.target.value)} />
            </VeField>
            <VeField label="Website" id="ve-banner-website">
              <input id="ve-banner-website" className="ve-input" value={banner.website}
                placeholder="nike.com"
                onChange={(e) => setBanner("website", e.target.value)} />
            </VeField>
          </div>
        </>
      );
    }
  }

  const hasBannerData = Boolean(
    banner.companyName || banner.phone || banner.address || banner.website
  );

  const showBanner = activeTab === "banner" && (
    banner.companyName || banner.phone || banner.address || banner.website
  );

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="ve-shell">

      {/* ── Top bar ─────────────────────────────────── */}
      <div className="ve-topbar">
        <div className="ve-topbar-left">
          <span className="ve-brand">
            <span className="ve-brand-mark">⚡</span>
            AdCraft Studio
          </span>
          <span className="ve-title">{scraped.business_name}</span>
        </div>
        <div className="ve-topbar-right">
          <button id="ve-download-btn" className="ve-ghost-btn" onClick={onDownload}>
            Download MP4
          </button>
          <button id="ve-back-btn" className="ve-ghost-btn" onClick={onBack}>
            New ad
          </button>
          <button
            id="ve-save-export-btn"
            className="ve-save-btn"
            onClick={handleSaveExport}
            disabled={rendering}
          >
            {rendering ? "Re-rendering…" : globalSaved ? "Saved" : "Save & re-render"}
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
                crossOrigin="anonymous"
                controls={false}
                onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
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
                    {banner.companyName}
                  </span>
                  <div className="ve-banner-contacts">
                    {banner.phone   && <span>📞 {banner.phone}</span>}
                    {banner.address && <span>📍 {banner.address}</span>}
                  </div>
                  {banner.website && (
                    <span
                      className="ve-banner-pill"
                      style={{ background: edits.accentColor }}
                    >
                      {banner.website}
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
                {fmt(currentTime)} / {fmt(duration)}
              </span>
              <span className="ve-tl-hint">Click the timeline to scrub</span>
            </div>

            {/* Lanes. Widths are the real thing: the renderer splits the
                background into equal scenes, and loops music to the full
                duration. The banner lane is dashed because it is previewed
                here but is not in the MP4 yet. */}
            <div className="ve-tl-body">
              <div className="ve-tl-gutter">
                <span className="ve-tl-gutter-head" />
                <span className="ve-tl-lane-label">Video</span>
                <span className="ve-tl-lane-label">Voice</span>
                <span className="ve-tl-lane-label">Music</span>
                {hasBannerData && <span className="ve-tl-lane-label">Banner</span>}
              </div>

              <div
                className="ve-tl-lanes"
                ref={lanesRef}
                onClick={(e) => scrubTo(e.clientX)}
                role="presentation"
              >
                <div className="ve-tl-ruler">
                  {ticks.map((t) => (
                    <span
                      key={t.at}
                      className={`ve-tick${t.major ? " major" : ""}`}
                      style={{ left: `${(t.at / duration) * 100}%` }}
                    >
                      {t.major && <b>{fmt(t.at)}</b>}
                    </span>
                  ))}
                </div>

                <div className="ve-lane">
                  {Array.from({ length: SCENE_COUNT }, (_, i) => {
                    const img = sceneImage(i);
                    return (
                      <div
                        key={i}
                        className={`ve-clip ve-clip-video${activeScene === i ? " current" : ""}`}
                        style={{
                          left: `${(i / SCENE_COUNT) * 100}%`,
                          width: `${(1 / SCENE_COUNT) * 100}%`,
                        }}
                      >
                        {img && (
                          /* eslint-disable-next-line @next/next/no-img-element */
                          <img src={img} alt="" />
                        )}
                        <span className="ve-clip-name">Scene {i + 1}</span>
                      </div>
                    );
                  })}
                </div>

                <div className="ve-lane">
                  <div className="ve-clip ve-clip-voice" style={{ left: 0, width: "100%" }}>
                    <span className="ve-clip-name">Voiceover</span>
                  </div>
                </div>

                <div className="ve-lane">
                  <div className="ve-clip ve-clip-music" style={{ left: 0, width: "100%" }}>
                    <span className="ve-clip-name">Music bed — {edits.musicStyle}</span>
                  </div>
                </div>

                {hasBannerData && (
                  <div className="ve-lane">
                    <div className="ve-clip ve-clip-pending" style={{ left: 0, width: "100%" }}>
                      <span className="ve-clip-name">Bottom banner — preview only</span>
                    </div>
                  </div>
                )}

                {duration > 0 && (
                  <div
                    className="ve-playhead"
                    style={{ left: `${(currentTime / duration) * 100}%` }}
                    aria-hidden="true"
                  >
                    <span className="ve-playhead-grip" />
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className={`ve-notice${renderError ? " error" : ""}`} role="status">
        {renderError
          ? renderError
          : rendering
          ? "Re-rendering your ad — this takes about half a minute."
          : "Save & re-render rebuilds the MP4 with your text, voice, music, colours and scene images."}
      </div>

      {rendering && (
        <div className="ve-rerender-scrim" role="status" aria-live="polite">
          <div className="ve-rerender-card">
            <span className="ve-rerender-spinner" aria-hidden="true" />
            <p className="ve-rerender-title">Re-rendering your ad</p>
            <p className="ve-rerender-sub">
              Narration and music are being regenerated. About half a minute.
            </p>
          </div>
        </div>
      )}

      {pickerScene !== null && (
        <ScenePicker
          sceneLabel={`Scene #${pickerScene + 1}`}
          seedQuery={script.scene_description || scraped.business_name || "business"}
          onPick={(o) => pickScene(pickerScene, o)}
          onClose={() => setPickerScene(null)}
        />
      )}
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
