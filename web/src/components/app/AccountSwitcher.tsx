"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { ChevronDown } from "lucide-react";
import Link from "next/link";

import { Skeleton } from "@/components/ui/skeleton";
import { logout, useAdminStatus, useMe } from "@/lib/hooks";

const MENU: { label: string; href: string }[] = [
  { label: "Settings", href: "/dashboard/settings/general" },
  { label: "Advertisers", href: "/dashboard/settings/advertisers" },
  { label: "Billing", href: "/dashboard/settings/billing/balance" },
  { label: "Help center", href: "/help" },
];

export function AccountSwitcher() {
  const { data: me } = useMe();
  const { data: admin } = useAdminStatus();
  const menu = admin ? [...MENU, { label: "Admin", href: "/dashboard/admin" }] : MENU;
  // Until the real account arrives show a skeleton — never a made-up name like "Your account".
  if (!me?.active_account?.name) {
    return (
      <span className="flex items-center gap-2 px-2 py-1.5" aria-busy="true" aria-label="Loading account">
        <Skeleton className="h-6 w-6 bg-white/15" name="account" />
        <Skeleton className="h-3 w-24 bg-white/15" />
      </span>
    );
  }
  const accountName = me.active_account.name;
  const initial = accountName.charAt(0).toUpperCase();

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger className="flex items-center gap-2 rounded-[var(--radius-md)] px-2 py-1.5 text-sm text-[var(--color-nav-text)] hover:bg-white/10 focus:outline-none">
        <span
          className="grid h-6 w-6 place-items-center rounded-[var(--radius-sm)] text-xs font-semibold text-white"
          style={{ background: "var(--color-primary)" }}
        >
          {initial}
        </span>
        <span className="max-w-[140px] truncate">{accountName}</span>
        <ChevronDown className="h-4 w-4 opacity-70" />
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={8}
          className="z-50 min-w-[220px] rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-1 text-[var(--color-text-body)] shadow-[var(--shadow-pop)]"
        >
          <div className="px-3 py-2">
            <p className="text-sm font-semibold text-[var(--color-text)]">{accountName}</p>
            {me?.email && <p className="text-xs text-[var(--color-text-muted)]">{me.email}</p>}
          </div>
          <DropdownMenu.Separator className="my-1 h-px bg-[var(--color-border)]" />
          {menu.map((m) => (
            <DropdownMenu.Item key={m.href} asChild>
              <Link
                href={m.href}
                className="block cursor-pointer rounded-[var(--radius-sm)] px-3 py-2 text-sm hover:bg-[var(--color-bg-subtle)] focus:bg-[var(--color-bg-subtle)] focus:outline-none"
              >
                {m.label}
              </Link>
            </DropdownMenu.Item>
          ))}
          <DropdownMenu.Separator className="my-1 h-px bg-[var(--color-border)]" />
          <DropdownMenu.Item
            onSelect={(e) => {
              e.preventDefault();
              void logout();
            }}
            className="cursor-pointer rounded-[var(--radius-sm)] px-3 py-2 text-sm text-[var(--color-danger)] hover:bg-[var(--color-danger-50)] focus:bg-[var(--color-danger-50)] focus:outline-none"
          >
            Log out
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
