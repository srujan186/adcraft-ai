import type { ReactNode } from "react";

/** Centered empty state (docs/05): simple line illustration, bold title, muted line, optional action. */
export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-[var(--radius-lg)] border border-dashed border-[var(--color-border-strong)] bg-[var(--color-bg-subtle)] px-6 py-16 text-center">
      <div className="mb-4 text-[var(--color-text-muted)]" aria-hidden>
        {icon ?? <DefaultGlyph />}
      </div>
      <h3 className="text-base font-semibold text-[var(--color-text)]">{title}</h3>
      {description && <p className="mt-1 max-w-md text-sm text-[var(--color-text-muted)]">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

function DefaultGlyph() {
  return (
    <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="6" y="10" width="36" height="24" rx="3" />
      <path d="M18 40h12M24 34v6" />
    </svg>
  );
}

/**
 * M0 placeholder used by every not-yet-built screen so navigation works and the
 * status is honest about which milestone fills it in.
 */
export function MilestonePlaceholder({ milestone, feature }: { milestone: string; feature: string }) {
  return (
    <div className="px-8 py-8">
      <EmptyState
        title={`${feature} — building in ${milestone}`}
        description={`This screen's scaffold is in place. Its full behavior ships in ${milestone} per the build plan.`}
      />
    </div>
  );
}
