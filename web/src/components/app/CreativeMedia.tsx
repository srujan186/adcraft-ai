"use client";

import { Film } from "lucide-react";
import { useState } from "react";

/* Creative files can disappear on hosts without a persistent disk (the server restarts, the
 * database row survives). Fall back to a neutral icon/message instead of a broken image. */

export function CreativeThumb({ src, alt, className }: { src?: string | null; alt: string; className?: string }) {
  const [broken, setBroken] = useState(false);
  if (!src || broken) {
    return <Film className="h-5 w-5 text-[var(--color-text-muted)]" role="img" aria-label={`${alt} — preview unavailable`} />;
  }
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={alt} className={className} onError={() => setBroken(true)} />;
}

export function CreativeVideo({ src, className }: { src: string; className?: string }) {
  const [broken, setBroken] = useState(false);
  if (broken) {
    return (
      <div className="grid aspect-video w-full place-items-center rounded-[var(--radius-lg)] text-center text-sm text-white/80">
        <span>
          <Film className="mx-auto mb-2 h-6 w-6" aria-hidden />
          This video&apos;s file isn&apos;t available right now.
        </span>
      </div>
    );
  }
  return <video src={src} controls autoPlay className={className} onError={() => setBroken(true)} />;
}
