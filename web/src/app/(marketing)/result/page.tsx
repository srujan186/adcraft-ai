"use client";
import { useEffect, useMemo, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { videoFileUrl, type VideoResult } from "@/lib/legacy/api";
import { resultStore } from "@/lib/legacy/clientStore";
import VideoEditor from "./VideoEditor";

// The result IS the editor. Landing on a read-only summary and hiding the
// controls behind an "Edit video" button put the useful half of the product
// one click out of view.
export default function ResultPage() {
  const router = useRouter();

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

  const scraped = result.scraped;

  function handleDownload() {
    const a = document.createElement("a");
    a.href = videoSrc;
    a.download = `adcraft_${scraped.business_name.replace(/\s+/g, "_")}.mp4`;
    a.click();
  }

  return (
    <VideoEditor
      result={result}
      videoSrc={videoSrc}
      onDownload={handleDownload}
      onBack={() => router.push("/generate")}
    />
  );
}
