// lib/api.ts — typed API client for AdCraft AI backend

// Empty means same-origin: next.config.ts rewrites /api/* to the backend, so
// the browser never makes a cross-origin request. Set NEXT_PUBLIC_API_URL to an
// absolute URL only when the backend is on a different host.
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ScrapeResult {
  business_name: string;
  /** Photos found on the page, used as the ad's scenes. */
  images?: string[];
  description: string;
  /** The site the ad was built from — needed to re-render un-swapped scenes. */
  url?: string;
  tagline?: string;
  logo_url?: string;
  colors?: { primary: string; secondary: string; accent: string };
  screenshot_url?: string;
}

export interface AdScript {
  headline: string;
  subtext: string;
  cta: string;
  voiceover: string;
  music_style: string;
  scene_description: string;
  color_mood: string;
  key_message: string;
}

/** The ad's closing frame. Mirrors EndCard in backend/models/generate.py. */
export interface EndCardData {
  company_name: string;
  phone: string;
  email: string;
  address: string;
  website: string;
}

export interface VideoResult {
  video_url: string;
  render_id: string;
  /** How many shots the ad was cut from — varies with what the site yielded. */
  scene_count?: number;
  /**
   * What each scene was built from, one entry per scene: a URL, or "" for a
   * scene cut from a screenshot or stock clip, which cannot be asked for
   * again by name. The editor sends these back so deleting one scene does
   * not reshuffle the others.
   */
  scene_sources?: string[];
  /** Whether the rendered file already ends on a contact card. */
  has_end_card?: boolean;
  /** When that card takes over, in seconds. */
  end_card_at?: number | null;
  /** The details it was rendered with, so the editor knows what is baked in. */
  end_card?: EndCardData;
  script: AdScript;
  scraped: ScrapeResult;
}

export type AdStyle = "modern" | "bold" | "minimal" | "playful";

/** A stock photo from the editor's scene picker. */
export interface StockPhoto {
  id: number;
  alt: string;
  author: string;
  author_url: string;
  thumb: string;
  full: string;
}

// ─── API Calls ───────────────────────────────────────────────────────────────

export async function scrapeUrl(url: string): Promise<ScrapeResult> {
  const res = await fetch(`${BASE}/api/scrape`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? "Scrape failed");
  return json.data as ScrapeResult;
}

export async function generateVideo(
  url: string,
  adStyle: AdStyle,
  duration: 15 | 30,
  // Lets the generation overlay's close button actually abort the render
  // rather than just hiding itself while the request keeps running.
  signal?: AbortSignal
): Promise<VideoResult> {
  const res = await fetch(`${BASE}/api/generate/video`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, ad_style: adStyle, duration }),
    signal,
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? "Video generation failed");
  return json.data as VideoResult;
}

export interface RerenderPayload {
  business_name: string;
  duration: 15 | 30;
  url?: string;
  logo_url?: string;
  colors?: { primary: string; secondary: string; accent: string };
  script: {
    headline: string;
    subtext: string;
    cta: string;
    voiceover: string;
    music_style: string;
    scene_description: string;
  };
  /** One entry per scene; "" means "use the site's own image for this one". */
  scene_images?: string[];
  /** The site's photos, so un-replaced scenes keep the imagery they had. */
  content_images?: string[];
  /** Closing card details. Omit, or leave every field blank, for no card. */
  end_card?: EndCardData;
  /**
   * How many scenes to cut the footage into.
   *
   * Sent explicitly because the backend would otherwise infer it from how many
   * `scene_images` entries carry an image — which silently drops a slot the
   * user added with "+" but left for us to fill.
   */
  scene_count?: number;
}

/** Re-runs assembly against edited copy. No scrape, no LLM — 20-45s. */
export async function rerenderVideo(
  payload: RerenderPayload,
  signal?: AbortSignal
): Promise<{
  video_url: string;
  render_id: string;
  scene_count?: number;
  scene_sources?: string[];
  has_end_card?: boolean;
  end_card_at?: number | null;
}> {
  const res = await fetch(`${BASE}/api/generate/rerender`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? "Re-render failed");
  return json.data as {
    video_url: string;
    render_id: string;
    scene_count?: number;
    scene_sources?: string[];
    has_end_card?: boolean;
    end_card_at?: number | null;
  };
}

export async function searchPhotos(
  query: string,
  signal?: AbortSignal
): Promise<StockPhoto[]> {
  const res = await fetch(
    `${BASE}/api/media/photos?query=${encodeURIComponent(query)}&per_page=18`,
    { signal }
  );
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? "Image search failed");
  return json.data as StockPhoto[];
}

export function videoFileUrl(filename: string): string {
  // filename may be a full relative path like "output/ad_xxx.mp4" or just "ad_xxx.mp4"
  const name = filename.split("/").pop() ?? filename;
  return `${BASE}/api/output/${name}`;
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/api/health`);
    return res.ok;
  } catch {
    return false;
  }
}
