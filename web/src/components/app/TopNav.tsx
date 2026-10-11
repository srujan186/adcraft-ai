"use client";

import { Bell, Sparkles } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";
import { agentStore } from "@/lib/agentStore";
import { cn, PRODUCT_NAME } from "@/lib/utils";
import { AccountSwitcher } from "./AccountSwitcher";
import { TOP_NAV } from "./nav-data";

function isActive(pathname: string, href: string): boolean {
  if (href === "/dashboard") return pathname === "/dashboard";
  // Insights links to /insights/overview; match the /insights branch.
  const base = href.replace(/\/overview$/, "");
  return pathname === href || pathname.startsWith(base + "/") || pathname.startsWith(base);
}

export function TopNav() {
  const pathname = usePathname();

  return (
    <header
      className="sticky top-0 z-40 flex h-14 items-center gap-6 px-6"
      style={{ background: "var(--color-nav)", color: "var(--color-nav-text)" }}
    >
      <Link href="/dashboard" className="flex items-center gap-2 font-semibold text-white">
        <span
          className="grid h-7 w-7 place-items-center rounded-[var(--radius-md)] text-white"
          style={{ background: "var(--color-primary)" }}
          aria-hidden
        >
          <Sparkles className="h-4 w-4" />
        </span>
        {PRODUCT_NAME}
      </Link>

      <nav className="flex items-center gap-1 text-sm">
        {TOP_NAV.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "relative flex items-center gap-1.5 px-3 py-2 transition-colors",
                active ? "text-white" : "text-[var(--color-nav-text)] hover:text-white",
              )}
            >
              {item.label}
              {item.badge && (
                <span
                  className="rounded-full px-1.5 py-0.5 text-[10px] font-semibold text-white"
                  style={{ background: "var(--color-primary)" }}
                >
                  {item.badge}
                </span>
              )}
              {active && (
                <span
                  className="absolute inset-x-2 -bottom-[1px] h-0.5 rounded-full"
                  style={{ background: "var(--color-primary-300)" }}
                />
              )}
            </Link>
          );
        })}
      </nav>

      <div className="ml-auto flex items-center gap-3">
        <button
          type="button"
          aria-label="Notifications"
          className="grid h-9 w-9 place-items-center rounded-[var(--radius-md)] text-[var(--color-nav-text)] hover:bg-white/10"
        >
          <Bell className="h-5 w-5" />
        </button>
        <Button variant="navOutline" size="sm" onClick={() => agentStore.openAgent()}>
          <Sparkles className="h-4 w-4" />
          Ask Agent
        </Button>
        <AccountSwitcher />
      </div>
    </header>
  );
}
