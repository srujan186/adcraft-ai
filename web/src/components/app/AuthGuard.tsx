"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { isAuthed } from "@/lib/auth";

/** Client-side gate for /dashboard: bounce to /login when there's no session. */
export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [ok, setOk] = useState(false);

  useEffect(() => {
    if (!isAuthed()) {
      router.replace("/login");
    } else {
      setOk(true);
    }
  }, [router]);

  if (!ok) {
    // Only lasts until the session check runs after hydration: show the app's frame, no text.
    return (
      <div className="min-h-screen" aria-busy="true">
        <div className="h-14" style={{ background: "var(--color-nav)" }} />
      </div>
    );
  }
  return <>{children}</>;
}
