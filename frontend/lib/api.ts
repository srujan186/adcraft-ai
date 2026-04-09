// lib/api.ts — typed API client for AdCraft AI backend

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ScrapeResult {
  business_name: string;
  description: string;
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
  duration: 15 | 30
): Promise<VideoResult> {
  const res = await fetch(`${BASE}/api/generate/video`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, ad_style: adStyle, duration }),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? "Video generation failed");
  return json.data as VideoResult;
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
