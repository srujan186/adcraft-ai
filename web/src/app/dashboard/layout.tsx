import type { ReactNode } from "react";

import { AppShell } from "@/components/app/AppShell";
import { AuthGuard } from "@/components/app/AuthGuard";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <AppShell>{children}</AppShell>
    </AuthGuard>
  );
}
