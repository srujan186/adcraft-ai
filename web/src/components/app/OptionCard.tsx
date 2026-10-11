import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/** Radio-style selectable card (docs/05): selected = primary border + primary-50 bg. */
export function OptionCard({
  selected,
  onClick,
  title,
  description,
  icon,
  disabled,
}: {
  selected: boolean;
  onClick: () => void;
  title: string;
  description?: string;
  icon?: ReactNode;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "flex w-full items-start gap-3 rounded-[var(--radius-lg)] border p-4 text-left transition-colors disabled:opacity-50",
        selected
          ? "border-[var(--color-primary)] bg-[var(--color-primary-50)]"
          : "border-[var(--color-border)] bg-[var(--color-surface)] hover:border-[var(--color-border-strong)]",
      )}
    >
      {icon && <div className="mt-0.5 text-[var(--color-primary)]">{icon}</div>}
      <div className="min-w-0">
        <div className="font-medium text-[var(--color-text)]">{title}</div>
        {description && <div className="mt-0.5 text-xs text-[var(--color-text-muted)]">{description}</div>}
      </div>
    </button>
  );
}
