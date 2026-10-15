import { cn } from "@/lib/utils";

type Tone = "success" | "warning" | "danger" | "info" | "primary" | "slate";

const TONE: Record<Tone, string> = {
  success: "bg-[var(--color-success-50)] text-[var(--color-success)]",
  warning: "bg-[var(--color-warning-50)] text-[var(--color-warning)]",
  danger: "bg-[var(--color-danger-50)] text-[var(--color-danger)]",
  info: "bg-[var(--color-info-50)] text-[var(--color-info)]",
  primary: "bg-[var(--color-primary-50)] text-[var(--color-primary)]",
  slate: "bg-slate-100 text-slate-600",
};

// docs/05 status pills (+ creative review statuses)
const STATUS: Record<string, { tone: Tone; label: string; pulse?: boolean }> = {
  draft: { tone: "warning", label: "Draft" },
  in_review: { tone: "info", label: "In review" },
  scheduled: { tone: "info", label: "Scheduled" },
  learning: { tone: "primary", label: "Learning", pulse: true },
  delivering: { tone: "success", label: "Delivering" },
  paused: { tone: "slate", label: "Paused" },
  blocked: { tone: "danger", label: "Blocked" },
  completed: { tone: "slate", label: "Completed" },
  archived: { tone: "slate", label: "Archived" },
  // creative review
  pending: { tone: "warning", label: "Pending" },
  processing: { tone: "info", label: "Processing", pulse: true },
  approved: { tone: "success", label: "Approved" },
  rejected: { tone: "danger", label: "Rejected" },
  needs_changes: { tone: "warning", label: "Needs changes" },
  // audiences
  ready: { tone: "success", label: "Ready" },
  counting: { tone: "info", label: "Counting", pulse: true },
  no_data: { tone: "slate", label: "No data yet" },
  error: { tone: "danger", label: "Error" },
};

export function StatusPill({ status }: { status: string }) {
  const s = STATUS[status] ?? { tone: "slate" as Tone, label: status };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium capitalize",
        TONE[s.tone],
      )}
    >
      {s.pulse && <span className="lumen-pulse h-1.5 w-1.5 rounded-full bg-current" />}
      {s.label}
    </span>
  );
}
