"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { SETTINGS_NAV } from "@/components/app/nav-data";
import { cn } from "@/lib/utils";

export default function SettingsLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-[calc(100vh-56px)]">
      <aside className="w-[240px] shrink-0 border-r border-[var(--color-border)] px-3 py-6">
        <p className="px-3 pb-3 text-[30px] font-bold leading-none text-[var(--color-text)]">Settings</p>
        <nav className="mt-2 space-y-5">
          {SETTINGS_NAV.map((group) => (
            <div key={group.group}>
              <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
                {group.group}
              </p>
              <ul className="space-y-0.5">
                {group.items.map((item) => {
                  const active = pathname === item.href;
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        className={cn(
                          "block rounded-[var(--radius-sm)] px-3 py-1.5 text-sm",
                          active
                            ? "bg-[var(--color-primary-50)] font-medium text-[var(--color-primary)]"
                            : "text-[var(--color-text-body)] hover:bg-[var(--color-bg-subtle)]",
                        )}
                      >
                        {item.label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>
      </aside>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
