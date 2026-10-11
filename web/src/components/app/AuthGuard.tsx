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
    return (
      <div className="grid min-h-screen place-items-center text-sm text-[var(--color-text-muted)]">
        Loading…
      </div>
    );
  }
  return <>{children}</>;
}
