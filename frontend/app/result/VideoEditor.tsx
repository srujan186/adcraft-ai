"use client";
import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import "./editor.css";
import { rerenderVideo, type EndCardData, type VideoResult } from "@/lib/api";
import {
  bannerStore,
  resultStore,
  scenesStore,
  type BannerData,
  type SceneEdit,
  type SceneOverride,
  type SceneSlot,
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
    email: string;
    address: string;
    website: string;
  };
}

type TabId = "scenes" | "text" | "voiceover" | "music" | "colors" | "endcard";

// Mirrors ENDCARD_SECONDS in backend/services/video_assembler.py. The closing
// card covers the last few seconds, and the captions stop when it starts.
const ENDCARD_SECONDS = 3;

// Mirrors MAX_SCENES in backend/models/generate.py — the request is rejected
// above this, so the "+" has to stop offering it.
const MAX_SCENES = 12;

// Timeline magnification. 8x puts roughly two seconds across the panel, which
// is enough to separate the clips of a 12-scene 15s ad.
const MAX_ZOOM = 8;
const ZOOM_STEP = 1.5;

// How many shots the ad was cut from. The backend reports this per render —
// a page that yields four usable images makes a four-scene ad — so it is not a
// constant. This is only the fallback for results saved before it existed.
const DEFAULT_SCENE_COUNT = 6;

const TABS: { id: TabId; icon: string; label: string }[] = [
  { id: "scenes",    icon: "🎞️", label: "Scenes" },
  { id: "text",      icon: "📝", label: "Text" },
  { id: "voiceover", icon: "🎤", label: "Voice" },
  { id: "music",     icon: "🎵", label: "Music" },
  { id: "colors",    icon: "🎨", label: "Colors" },
  { id: "endcard",   icon: "📇", label: "End card" },
];

// Timeline lanes, and the panel each one edits.
const LANES: { id: string; label: string; tab: TabId }[] = [
  { id: "video",  label: "Video",  tab: "scenes" },
  { id: "voice",  label: "Voice",  tab: "voiceover" },
  { id: "music",  label: "Music",  tab: "music" },
  { id: "endcard", label: "End card", tab: "endcard" },
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
function useSceneThumbs(src: string, count: number, tailSeconds = 0) {
  const [thumbs, setThumbs] = useState<string[]>([]);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    if (!src || count < 1) return;
    let cancelled = false;

    const v = document.createElement("video");
    v.crossOrigin = "anonymous";
    v.preload = "auto";
    v.muted = true;

    const shots: string[] = [];
    let i = 0;

    const seekNext = () => {
      // Mid-point of each scene reads better than its first frame.
      //
      // Sample inside the footage, not the whole file: with an end card the
      // last scene's mid-point landed past the cut, so scene 6's thumbnail
      // was a picture of the contact card.
      const footage = Math.max(0.1, v.duration - tailSeconds);
      v.currentTime = Math.min(v.duration - 0.05, (footage / count) * (i + 0.5));
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
  }, [src, count, tailSeconds]);

  return { thumbs, duration };
}

/** Mirrors pick_cta_colors in services/video_assembler.py. */
function ctaColors(primary: string, accent: string): { bg: string; fg: string } {
  const lum = (hex: string) => {
    const h = hex.replace("#", "");
    if (h.length !== 6) return 0;
    const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  };
  for (const c of [accent, primary]) {
    const l = lum(c);
    // A near-black brand colour disappears into the scrim it sits on.
    if (l > 0.3) return { bg: c, fg: l > 0.62 ? "#0b0d14" : "#ffffff" };
  }
  return { bg: "#ffffff", fg: "#0b0d14" };
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
  const trackRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [playing, setPlaying] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>("scenes");
  // Timeline magnification. 1 = the whole ad across the panel; above that
  // the track overflows and scrolls, which is how you read a 12-scene cut.
  const [zoom, setZoom] = useState(1);
  const [pickerScene, setPickerScene] = useState<number | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
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

  // How many scenes the file on screen was actually cut into. `??` alone
  // would let a 0 through, and every scene calculation divides by this — a
  // zero count means NaN timecodes and an empty editor.
  const renderedScenes = result.scene_count || DEFAULT_SCENE_COUNT;

  // The end card in the file on screen — not the one being edited.
  const renderedTail = result.has_end_card ? ENDCARD_SECONDS : 0;
  const { thumbs, duration } = useSceneThumbs(videoSrc, renderedScenes, renderedTail);

  // Where the footage stops and the card takes over, in the current file.
  const footageEnd = duration ? Math.max(0.1, duration - renderedTail) : 0;

  const scenesRaw = useSyncExternalStore(
    scenesStore.subscribe,
    scenesStore.getSnapshot,
    scenesStore.getServerSnapshot
  );

  // What the file on screen is actually made of, one entry per scene. The
  // backend names the source it used so a scene can be handed back by name;
  // "" means it came from a screenshot or stock clip and cannot be.
  const baseSlots = useMemo<SceneSlot[]>(() => {
    const srcs = result.scene_sources ?? [];
    return Array.from({ length: renderedScenes }, (_, i) => ({
      src: srcs[i] ?? "",
      kind: (srcs[i] ? "page" : "auto") as SceneSlot["kind"],
      thumbIndex: i,
    }));
  }, [result.scene_sources, renderedScenes]);

  // Stamped with the render it was built against. Even if a reset is missed
  // somewhere, a list from a different ad is ignored rather than pasted into
  // whatever is on screen now.
  const editedSlots = useMemo<SceneSlot[] | null>(() => {
    if (!scenesRaw) return null;
    try {
      const parsed = JSON.parse(scenesRaw) as Partial<SceneEdit>;
      if (parsed.renderId !== result.render_id) return null;
      return Array.isArray(parsed.slots) ? parsed.slots : null;
    } catch {
      return null;
    }
  }, [scenesRaw, result.render_id]);

  const slots = editedSlots ?? baseSlots;
  const sceneCount = slots.length;
  const slotsDirty =
    editedSlots !== null && JSON.stringify(editedSlots) !== JSON.stringify(baseSlots);

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
      companyName: result.end_card?.company_name ?? scraped.business_name ?? "",
      phone:       result.end_card?.phone   ?? "",
      email:       result.end_card?.email   ?? "",
      address:     result.end_card?.address ?? "",
      website:     result.end_card?.website ?? "",
    },
  });

  // Saved banner values take precedence over this component's initial state.
  const banner = { ...edits.banner, ...storedBanner };

  // What the renderer would be sent. Mirrors EndCard in models/generate.py.
  const cardDetails: EndCardData = {
    company_name: banner.companyName.trim(),
    phone:        banner.phone.trim(),
    email:        banner.email.trim(),
    address:      banner.address.trim(),
    website:      banner.website.trim(),
  };

  // A company name alone is not an end card — and the name is pre-filled from
  // the scrape, so treating it as content would bolt three seconds of card
  // onto every re-render whether or not anyone opened this panel. At least one
  // way to get in touch has to be there.
  const hasCardData = Boolean(
    cardDetails.phone || cardDetails.email || cardDetails.address || cardDetails.website
  );

  const renderedCard = result.end_card;
  const cardDirty =
    hasCardData !== Boolean(result.has_end_card) ||
    (hasCardData &&
      (cardDetails.company_name !== (renderedCard?.company_name ?? "") ||
        cardDetails.phone       !== (renderedCard?.phone   ?? "") ||
        cardDetails.email       !== (renderedCard?.email   ?? "") ||
        cardDetails.address     !== (renderedCard?.address ?? "") ||
        cardDetails.website     !== (renderedCard?.website ?? "")));

  // ── The timeline's layout, and how it maps to the video ───────────────────
  //
  // The timeline describes the render that is *coming*; the <video> plays the
  // one that is *here*. Keeping two scales caused both of the bugs this
  // replaced: the end-card clip overlapped the last scene by its own width,
  // and the playhead sat over a different clip from the frame on screen.
  //
  // With nothing pending the two spaces are identical and these are no-ops.

  /** Seconds of footage the next render will have, before any end card. */
  const projectedFootage = duration
    ? Math.max(0.1, duration - (hasCardData ? ENDCARD_SECONDS : 0))
    : 0;

  /** The share of the track the footage occupies. The card takes the rest. */
  const footagePct = duration ? (projectedFootage / duration) * 100 : 100;

  /** How long one scene of the *rendered* file runs. */
  const renderedPerScene = renderedScenes ? footageEnd / renderedScenes : 0;

  /** The slot currently showing scene `k` of the rendered file. */
  function slotOfRendered(k: number): number {
    const i = slots.findIndex((s) => s.thumbIndex === k);
    return i >= 0 ? i : Math.min(k, sceneCount - 1);
  }

  /** Real video time -> where that frame sits on the timeline, in %. */
  function timeToPct(time: number): number {
    if (!duration || !renderedPerScene) return 0;
    if (time >= footageEnd) {
      // Past the footage: inside the rendered file's own card, if it has one.
      const tail = Math.max(0.001, duration - footageEnd);
      const into = Math.min(1, (time - footageEnd) / tail);
      return footagePct + into * (100 - footagePct);
    }
    const k = time / renderedPerScene;
    const whole = Math.min(renderedScenes - 1, Math.floor(k));
    return ((slotOfRendered(whole) + (k - whole)) / sceneCount) * footagePct;
  }

  /** A point on the timeline -> the video time to seek to, or null for none. */
  function pctToTime(pct: number): number | null {
    if (!duration || !renderedPerScene) return null;
    // The card is not footage; there is nothing inside it to scrub through.
    if (pct >= footagePct) return footageEnd;
    const pos = (pct / footagePct) * sceneCount;
    const idx = Math.min(sceneCount - 1, Math.floor(pos));
    const slot = slots[idx];
    // A scene no render has produced has no frame to seek to.
    if (slot?.thumbIndex == null) return null;
    return (slot.thumbIndex + (pos - idx)) * renderedPerScene;
  }

  const playheadPct = timeToPct(currentTime);
  const inCardWindow = duration > 0 && playheadPct >= footagePct - 0.01;

  /** The scene under the playhead, or -1 while the end card is showing. */
  const activeScene = inCardWindow
    ? -1
    : Math.min(
        sceneCount - 1,
        Math.max(0, Math.floor((playheadPct / footagePct) * sceneCount))
      );

  // ── Helpers ────────────────────────────────────────────────────────────────

  function set<K extends keyof Edits>(key: K, value: Edits[K]) {
    setEdits((e) => ({ ...e, [key]: value }));
  }

  function setBanner(field: keyof Edits["banner"], value: string) {
    const next = { ...banner, [field]: value };
    setEdits((e) => ({ ...e, banner: next }));
    // Publish immediately so the result page's panel reflects it.
    bannerStore.write({
      companyName:  next.companyName,
      phone:        next.phone,
      email:        next.email,
      address:      next.address,
      website:      next.website,
      primaryColor: edits.primaryColor,
      accentColor:  edits.accentColor,
    });
  }

  function writeSlots(next: SceneSlot[]) {
    scenesStore.write({ renderId: result.render_id, slots: next });
  }

  /** Swap one scene's picture for an upload or a stock photo. */
  function pickScene(index: number, override: SceneOverride) {
    const next = slots.map((s, i) =>
      i === index
        ? {
            ...s,
            src: override.src,
            kind: override.kind,
            credit: override.credit,
            creditUrl: override.creditUrl,
          }
        : s
    );
    writeSlots(next);
    setPickerScene(null);
    // Show the change straight away. The live preview mirrors the scene under
    // the playhead, so without this a swap only updated the timeline thumbnail
    // while the big preview kept showing whatever scene was playing. Pause and
    // seek to the scene just changed so its new image is on screen.
    const v = videoRef.current;
    if (v) { v.pause(); setPlaying(false); }
    showScene(index);
  }

  /** Append a scene and open the picker on it straight away. */
  function addScene() {
    if (sceneCount >= MAX_SCENES) return;
    setActiveTab("scenes");
    // No thumbIndex: no render has produced this one, so there is no frame to
    // show for it and nowhere to seek to.
    writeSlots([...slots, { src: "", kind: "auto" }]);
    setPickerScene(sceneCount);
  }

  /** Remove a scene outright. The rest keep their own pictures. */
  function deleteScene(index: number) {
    if (sceneCount <= 1) return;   // an ad with no scenes is not an ad
    writeSlots(slots.filter((_, i) => i !== index));
    setPickerScene(null);
  }

  /** Put a scene back to whatever the current render used for it. */
  function clearScene(index: number) {
    const slot = slots[index];
    const original =
      slot.thumbIndex != null ? baseSlots[slot.thumbIndex] : undefined;
    writeSlots(
      slots.map((s, i) => (i === index ? original ?? { src: "", kind: "auto" } : s))
    );
  }

  /** The picture shown for a scene: the chosen image, else its rendered frame. */
  function sceneImage(i: number): string {
    const slot = slots[i];
    if (!slot) return "";
    if (slot.kind === "upload" || slot.kind === "stock") return slot.src;
    if (slot.thumbIndex != null) return thumbs[slot.thumbIndex] ?? "";
    return "";
  }

  function sceneRange(i: number): string {
    if (!duration) return "—";
    // Once the list has been edited these are where the scenes *will* fall,
    // not where they are now — the panel header says so.
    const footage = Math.max(
      0.1,
      duration - (hasCardData ? ENDCARD_SECONDS : 0)
    );
    const per = footage / sceneCount;
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

  // The player shows the *rendered* file, so text and scene edits are
  // invisible until a re-render. When anything differs, overlay a live
  // composition instead so you can see what you are actually changing.
  const dirty =
    edits.headline !== script.headline ||
    edits.subtext !== script.subtext ||
    edits.cta !== script.cta ||
    // The renderer re-synthesises narration from this, so it very much counts
    // as a change — leaving it out left Save disabled after a script rewrite.
    edits.voiceover !== script.voiceover ||
    edits.musicStyle !== script.music_style ||
    edits.primaryColor !== (scraped.colors?.primary ?? "#1a1a2e") ||
    edits.accentColor !== (scraped.colors?.accent ?? "#6c63ff") ||
    // The end card is composited into the MP4 now, so changing it really does
    // change the file. While it was preview-only this was deliberately left
    // out, because re-rendering would have returned an identical video.
    cardDirty ||
    // Adding, deleting or replacing a scene all change how the footage is
    // cut, even when no new picture was chosen.
    slotsDirty;

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
        // One entry per scene, in order. A named source is re-fetched as-is,
        // so a scene survives its neighbours being deleted; "" asks the
        // backend to fill that slot from the page's own photography.
        scene_images: slots.map((s) => s.src),
        // Without these the backend would re-shoot un-replaced scenes from the
        // site, losing the photography the ad was originally cut from.
        content_images: scraped.images ?? [],
        // Omitted entirely when there is nothing to put on it, so the ad keeps
        // its full duration of footage.
        end_card: hasCardData ? cardDetails : undefined,
        // Say the count outright. Inferring it from "entries that carry an
        // image" would silently drop a slot the user added but left empty.
        scene_count: sceneCount,
      });

      // Writing the store re-renders the page with the new file, which flows
      // back down as a fresh videoSrc. This component keeps its edit state.
      // Store the edited script too. Without this `dirty` stays true and the
      // preview keeps covering a render that already matches it.
      resultStore.write({
        ...result,
        video_url: fresh.video_url,
        render_id: fresh.render_id,
        // A re-render does not always cut the same number of scenes — a
        // partial swap with no page images to fill the gaps yields fewer.
        // Dropping this left the scene list and timeline splitting the new
        // file into the *old* count, so every thumbnail was off.
        scene_count: fresh.scene_count ?? result.scene_count,
        scene_sources: fresh.scene_sources ?? [],
        // What the new file actually contains, so `cardDirty` settles back to
        // false and the preview stops covering a render that already matches.
        has_end_card: fresh.has_end_card ?? false,
        end_card_at: fresh.end_card_at ?? null,
        end_card: hasCardData ? cardDetails : undefined,
        script: {
          ...result.script,
          headline: edits.headline,
          subtext: edits.subtext,
          cta: edits.cta,
          voiceover: edits.voiceover,
          music_style: edits.musicStyle,
        },
        scraped: {
          ...result.scraped,
          colors: {
            primary: edits.primaryColor,
            secondary: scraped.colors?.secondary ?? "#ffffff",
            accent: edits.accentColor,
          },
        },
      });
      // The new file *is* the scene list now, so the edit layer goes away
      // and baseSlots is rebuilt from the render that just landed.
      scenesStore.clear();

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
    const el = trackRef.current;
    const v = videoRef.current;
    if (!el || !v || !duration) return;
    const rect = el.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    // Through the layout, not straight to `ratio * duration`: where you click
    // is a position in the *coming* render, which is not the same instant in
    // the file on screen whenever a card or a scene is pending.
    const at = pctToTime(ratio * 100);
    if (at == null) return;
    v.currentTime = at;
    setCurrentTime(at);
  }

  /** Jump the preview to the start of a scene. */
  function showScene(i: number) {
    const v = videoRef.current;
    const at2 = slots[i]?.thumbIndex;
    // Seek to where this scene sits in the file on screen. A slot no render
    // has produced has nowhere to go, and after a delete the list index and
    // the file's own scene order no longer agree — hence thumbIndex.
    if (!v || !duration || at2 == null) return;
    const at = (footageEnd / renderedScenes) * at2;
    v.currentTime = at;
    setCurrentTime(at);
  }

  // Follow the playhead when zoomed in, or it runs off the visible slice and
  // the timeline stops describing what you are watching. Only while playing,
  // so it never fights a scroll you made yourself.
  useEffect(() => {
    if (!playing || zoom === 1) return;
    const sc = scrollRef.current;
    const tr = trackRef.current;
    if (!sc || !tr || !duration) return;

    const x = (currentTime / duration) * tr.clientWidth;
    const left = sc.scrollLeft;
    const right = left + sc.clientWidth;
    if (x < left + 40 || x > right - 80) {
      sc.scrollLeft = Math.max(0, x - sc.clientWidth / 2);
    }
  }, [currentTime, playing, zoom, duration]);

  function togglePlay() {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) {
      // play() rejects if the browser blocks it or the source is still
      // loading. Setting `playing` optimistically left the button stuck on
      // pause over a video that never started.
      v.play().then(
        () => setPlaying(true),
        () => setPlaying(false)
      );
    } else {
      v.pause();
      setPlaying(false);
    }
  }

  // ── Panel content ──────────────────────────────────────────────────────────

  function renderPanel() {
    switch (activeTab) {
      case "scenes": return (
        <>
          <div className="ve-panel-header">
            <div className="ve-panel-title">Scenes</div>
            <div className="ve-panel-sub">
              {sceneCount} shots, split evenly across the footage
              {result.has_end_card ? " before the end card" : ""}
            </div>
          </div>
          <div className="ve-panel-body">
            <div className="ve-scene-list">
              {slots.map((slot, i) => {
                const swapped = slot.kind === "upload" || slot.kind === "stock";
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
                      {sceneCount > 1 && (
                        <button
                          className="ve-scene-delete"
                          id={`ve-scene-delete-${i}`}
                          title={`Delete scene ${i + 1}`}
                          aria-label={`Delete scene ${i + 1}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteScene(i);
                          }}
                        >
                          ×
                        </button>
                      )}
                    </div>
                    <div className="ve-scene-meta">
                      <p className="ve-scene-name">Scene #{i + 1}</p>
                      <p className="ve-scene-time">{sceneRange(i)}</p>
                      {activeScene === i && (
                        <p className="ve-scene-now">Currently visible</p>
                      )}
                      {slot.thumbIndex == null && !swapped && (
                        <p className="ve-scene-hint">
                          Pick an image, or leave it and we&rsquo;ll use one from
                          your site
                        </p>
                      )}
                      {swapped && (
                        <p className="ve-scene-swapped">
                          <span className="ve-scene-src">
                            {slot.kind === "upload" ? "Your image" : `Stock · ${slot.credit}`}
                          </span>
                          {slot.thumbIndex != null && (
                            <button
                              className="ve-scene-reset"
                              onClick={(e) => {
                                e.stopPropagation();
                                clearScene(i);
                              }}
                            >
                              Reset
                            </button>
                          )}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="ve-scene-actions">
              <button
                id="ve-add-scene"
                className="ve-add-scene"
                onClick={addScene}
                disabled={sceneCount >= MAX_SCENES}
              >
                + Add scene
              </button>
              {slotsDirty && (
                <button
                  id="ve-reset-scenes"
                  className="ve-remove-scene"
                  onClick={() => scenesStore.clear()}
                  title="Put the scene list back to the rendered ad"
                >
                  Reset all
                </button>
              )}
            </div>
            {sceneCount >= MAX_SCENES && (
              <p className="ve-panel-note">
                {MAX_SCENES} scenes is the maximum — past that each shot is too
                brief to register.
              </p>
            )}
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

      case "endcard": return (
        <>
          <div className="ve-panel-header">
            <div className="ve-panel-title">📇 End Card</div>
            <div className="ve-panel-sub">
              The ad’s closing {ENDCARD_SECONDS} seconds — your logo, name and
              how to get in touch
            </div>
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
            <VeField label="Email" id="ve-banner-email">
              <input id="ve-banner-email" className="ve-input" type="email" value={banner.email}
                placeholder="hello@nike.com"
                onChange={(e) => setBanner("email", e.target.value)} />
            </VeField>
            <VeField label="Website" id="ve-banner-website">
              <input id="ve-banner-website" className="ve-input" value={banner.website}
                placeholder="nike.com"
                onChange={(e) => setBanner("website", e.target.value)} />
            </VeField>
            <VeField label="Address" id="ve-banner-address">
              <input id="ve-banner-address" className="ve-input" value={banner.address}
                placeholder="One Bowerman Drive, OR"
                onChange={(e) => setBanner("address", e.target.value)} />
            </VeField>
            <p className="ve-panel-note">
              {hasCardData
                ? `The card uses your brand colour and logo, and replaces the last ${ENDCARD_SECONDS}s of footage.`
                : "Add a phone number, email, website or address and the card is added to the end of your ad."}
            </p>
          </div>
        </>
      );
    }
  }

  // Show the card over the player while you are building it, and whenever the
  // playhead is in its window but the rendered file does not match yet.
  const showCardPreview = hasCardData && (activeTab === "endcard" || (cardDirty && inCardWindow));

  // Captions stop when the card starts, so the live caption preview has to as
  // well — otherwise it previews a frame the renderer will never produce.
  const showLiveCaptions = dirty && !playing && !(hasCardData && inCardWindow);

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
          {/* One commit action, not two. "Apply Changes" used to live here and
              only wrote to sessionStorage — edits already show in the preview,
              so it read as the button that should have applied them. */}
          <div className="ve-panel-save">
            <button
              id="ve-apply-btn"
              className="ve-apply-btn"
              onClick={handleSaveExport}
              disabled={rendering || !dirty}
            >
              {rendering
                ? "Re-rendering…"
                : dirty
                ? "Save & re-render"
                : "No changes to apply"}
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
                // Track the element's real state rather than guessing at it in
                // togglePlay — the video also stops on its own (end of file,
                // a stalled source), and the button used to keep showing
                // "pause" over a video that was not playing.
                onPlay={() => setPlaying(true)}
                onPause={() => setPlaying(false)}
                onEnded={() => setPlaying(false)}
                style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
              />
              {/* Live composition of the current edits. Geometry mirrors
                  assemble_with_ffmpeg: a black scrim at alpha 150, headline
                  64px at y=180, subtext 36px at y=340, CTA at y=520 on a
                  1280x720 frame — expressed here as cq units so it scales. */}
              {showLiveCaptions && (
                <div className="ve-live" aria-hidden="true">
                  {sceneImage(activeScene) && (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img className="ve-live-bg" src={sceneImage(activeScene)} alt="" />
                  )}
                  <div className="ve-live-scrim" />
                  <p className="ve-live-headline">{edits.headline}</p>
                  <p className="ve-live-subtext">{edits.subtext}</p>
                  {edits.cta && (
                    <span
                      className="ve-live-cta"
                      style={(() => {
                        const c = ctaColors(edits.primaryColor, edits.accentColor);
                        return { background: c.bg, color: c.fg };
                      })()}
                    >
                      {edits.cta}
                    </span>
                  )}
                  <span className="ve-live-chip">
                    Preview of your edits — press play to watch the current render
                  </span>
                </div>
              )}

              {/* The closing card, drawn the way the renderer draws it. */}
              {showCardPreview && (
                <div
                  className="ve-endcard"
                  style={{ background: edits.primaryColor }}
                  aria-hidden="true"
                >
                  {scraped.logo_url && (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img className="ve-endcard-logo" src={scraped.logo_url} alt="" />
                  )}
                  {banner.companyName && (
                    <p className="ve-endcard-name">{banner.companyName}</p>
                  )}
                  {banner.companyName && (
                    <span
                      className="ve-endcard-rule"
                      style={{ background: edits.accentColor }}
                    />
                  )}
                  {banner.phone   && <p className="ve-endcard-row">{banner.phone}</p>}
                  {banner.email   && <p className="ve-endcard-row">{banner.email}</p>}
                  {banner.website && <p className="ve-endcard-row">{banner.website}</p>}
                  {banner.address && <p className="ve-endcard-row">{banner.address}</p>}
                  {cardDirty && (
                    <span className="ve-live-chip">
                      Preview of your end card — save to render it
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

              <div className="ve-tl-zoom">
                <button
                  id="ve-zoom-out"
                  className="ve-zoom-btn"
                  onClick={() => setZoom((z) => Math.max(1, z / ZOOM_STEP))}
                  disabled={zoom <= 1}
                  title="Zoom out"
                  aria-label="Zoom out"
                >
                  −
                </button>
                <span className="ve-zoom-val">{Math.round(zoom * 100)}%</span>
                <button
                  id="ve-zoom-in"
                  className="ve-zoom-btn"
                  onClick={() => setZoom((z) => Math.min(MAX_ZOOM, z * ZOOM_STEP))}
                  disabled={zoom >= MAX_ZOOM}
                  title="Zoom in"
                  aria-label="Zoom in"
                >
                  +
                </button>
                <button
                  id="ve-zoom-fit"
                  className="ve-zoom-btn wide"
                  onClick={() => setZoom(1)}
                  disabled={zoom === 1}
                  title="Fit the whole ad"
                >
                  Fit
                </button>
              </div>
            </div>

            {/* Lanes. Widths are the real thing: the renderer splits the
                background into equal scenes, and loops music to the full
                duration. The banner lane is dashed because it is previewed
                here but is not in the MP4 yet. */}
            <div className="ve-tl-body">
              {/* Each lane opens the panel that edits it — a timeline where
                  clicking the Music track does nothing is just a picture. */}
              <div className="ve-tl-gutter">
                <span className="ve-tl-gutter-head" />
                {LANES.filter((l) => l.id !== "endcard" || hasCardData).map((lane) => (
                  <button
                    key={lane.id}
                    type="button"
                    id={`ve-lane-${lane.id}`}
                    className={`ve-tl-lane-label${activeTab === lane.tab ? " active" : ""}`}
                    onClick={() => setActiveTab(lane.tab)}
                    title={`Edit ${lane.label.toLowerCase()}`}
                  >
                    {lane.label}
                  </button>
                ))}
              </div>

              {/* The track is the only thing that scales. Clip positions stay
                  in % of it, so they remain true to time at any zoom. */}
              <div className="ve-tl-scroll" ref={scrollRef}>
                <div
                  className="ve-tl-track"
                  ref={trackRef}
                  style={{ width: `${zoom * 100}%` }}
                >
                <div
                  className="ve-tl-ruler"
                  onClick={(e) => scrubTo(e.clientX)}
                  role="presentation"
                >
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

                <div
                  className={`ve-lane${activeTab === "scenes" ? " active" : ""}`}
                  onClick={(e) => scrubTo(e.clientX)}
                  role="presentation"
                >
                  {/* The scenes share the footage, which ends where the
                      card begins. Laying them across the whole duration made
                      the last clip sit underneath the end card's lane. */}
                  {slots.map((slot, i) => {
                    const img = sceneImage(i);
                    const span = (footagePct / sceneCount);
                    // Nothing rendered behind this one yet, so it cannot be
                    // scrubbed to.
                    const pending = slot.thumbIndex == null;
                    return (
                      <div
                        key={i}
                        className={
                          "ve-clip ve-clip-video" +
                          (activeScene === i ? " current" : "") +
                          (pending ? " pending" : "")
                        }
                        style={{ left: `${span * i}%`, width: `${span}%` }}
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveTab("scenes");
                          // A slot with no footage behind it cannot be seeked
                          // to, so open its picker instead.
                          if (pending) setPickerScene(i);
                          else showScene(i);
                        }}
                        role="presentation"
                      >
                        {img && (
                          /* eslint-disable-next-line @next/next/no-img-element */
                          <img src={img} alt="" />
                        )}
                        {/* "Scene" drops out on a narrow clip (container
                            query in editor.css) so the number always fits. */}
                        <span className="ve-clip-name">
                          <span className="ve-clip-word">Scene </span>
                          {i + 1}
                        </span>
                      </div>
                    );
                  })}

                </div>

                <div
                  className={`ve-lane${activeTab === "voiceover" ? " active" : ""}`}
                  onClick={(e) => scrubTo(e.clientX)}
                  role="presentation"
                >
                  <div
                    className="ve-clip ve-clip-voice"
                    style={{ left: 0, width: "100%" }}
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveTab("voiceover");
                    }}
                    role="presentation"
                  >
                    <span className="ve-clip-name">Voiceover</span>
                  </div>
                </div>

                <div
                  className={`ve-lane${activeTab === "music" ? " active" : ""}`}
                  onClick={(e) => scrubTo(e.clientX)}
                  role="presentation"
                >
                  <div
                    className="ve-clip ve-clip-music"
                    style={{ left: 0, width: "100%" }}
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveTab("music");
                    }}
                    role="presentation"
                  >
                    <span className="ve-clip-name">Music bed — {edits.musicStyle}</span>
                  </div>
                </div>

                {hasCardData && (
                  <div
                    className={`ve-lane${activeTab === "endcard" ? " active" : ""}`}
                    onClick={(e) => scrubTo(e.clientX)}
                    role="presentation"
                  >
                    {/* Sits at the end, the length it actually runs for — it is
                        a real segment of the video now, not a full-width
                        placeholder for something that never rendered. */}
                    <div
                      className="ve-clip ve-clip-endcard"
                      /* Begins where the last scene clip ends, by
                         construction, so it can never sit on top of one. */
                      style={{
                        left:  `${footagePct}%`,
                        width: `${100 - footagePct}%`,
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        setActiveTab("endcard");
                        if (duration) {
                          const v = videoRef.current;
                          if (v) { v.currentTime = footageEnd; setCurrentTime(footageEnd); }
                        }
                      }}
                      role="presentation"
                    >
                      <span className="ve-clip-name">End card</span>
                    </div>
                  </div>
                )}

                {duration > 0 && (
                  <div
                    className="ve-playhead"
                    style={{ left: `${playheadPct}%` }}
                    aria-hidden="true"
                  >
                    <span className="ve-playhead-grip" />
                  </div>
                )}
                </div>
              </div>

              {/* Outside the track on purpose. Inside it, the button either
                  fell off the right edge (no end card, so the clips reach
                  100%) or sat on top of the last clip. */}
              <div className="ve-tl-aside">
                <span className="ve-tl-gutter-head" />
                <button
                  id="ve-tl-add-scene"
                  className="ve-add-slot"
                  onClick={addScene}
                  disabled={sceneCount >= MAX_SCENES}
                  title={
                    sceneCount >= MAX_SCENES
                      ? `${MAX_SCENES} scenes is the maximum`
                      : "Add a scene"
                  }
                  aria-label="Add a scene"
                >
                  +
                </button>
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
