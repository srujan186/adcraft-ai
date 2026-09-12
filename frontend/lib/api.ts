// lib/api.ts — typed API client for AdCraft AI backend

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ScrapeResult {
  business_name: string;
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

export interface VideoResult {
  video_url: string;
  render_id: string;
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
  /** One entry per scene; "" means "use the live site for this one". */
  scene_images?: string[];
}

/** Re-runs assembly against edited copy. No scrape, no LLM — 20-45s. */
export async function rerenderVideo(
  payload: RerenderPayload,
  signal?: AbortSignal
): Promise<{ video_url: string; render_id: string }> {
  const res = await fetch(`${BASE}/api/generate/rerender`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? "Re-render failed");
  return json.data as { video_url: string; render_id: string };
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
