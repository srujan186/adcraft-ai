import type { ReactNode } from "react";

import { AgentPanel } from "./AgentPanel";
import { TopNav } from "./TopNav";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen" style={{ background: "var(--color-bg)" }}>
      <TopNav />
      <main className="mx-auto w-full max-w-[1280px]">{children}</main>
      <AgentPanel />
    </div>
  );
}
