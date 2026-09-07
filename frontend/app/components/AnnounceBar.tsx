"use client";
import { useState } from "react";
import Link from "next/link";

export default function AnnounceBar() {
  const [open, setOpen] = useState(true);
  if (!open) return null;

  return (
    <div className="announce">
      <span>
        ✨ AdCraft turns any business URL into a finished video ad —{" "}
        <Link href="/generate">try it free</Link>
      </span>
      <button
        className="announce-close"
        onClick={() => setOpen(false)}
        aria-label="Dismiss announcement"
      >
        ×
      </button>
    </div>
  );
}
