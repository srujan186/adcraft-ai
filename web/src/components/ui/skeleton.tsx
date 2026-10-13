import { cn } from "@/lib/utils";

/** Grey placeholder block shown while data loads — never placeholder text or names. */
export function Skeleton({ className, name }: { className?: string; name?: string }) {
  return (
    <span
      aria-hidden
      data-skeleton={name}
      className={cn("block rounded-[var(--radius-sm)] bg-[var(--color-bg-subtle)] motion-safe:animate-pulse", className)}
    />
  );
}
