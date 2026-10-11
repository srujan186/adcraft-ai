"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Lightbulb } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";

export interface Rec {
  id: string;
  type: string;
  title: string;
  body: string;
  projected: { metric?: string; current?: number; projected?: number; uplift_pct?: number };
}

const REJECT_REASONS: Record<string, string[]> = {
  increase_budget: ["Budget is capped", "Results not good enough yet", "Not now"],
  extend_attribution_window: ["I track results outside AdCraft AI", "Not now"],
  switch_to_auto_bidding: ["I use manual bidding on purpose", "Not now"],
  expand_audience: ["My targeting is narrow on purpose", "Not now"],
};

export function RecommendationCard({ rec }: { rec: Rec }) {
  const qc = useQueryClient();
  const [rejecting, setRejecting] = useState(false);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["recommendations"] });
    qc.invalidateQueries({ queryKey: ["campaigns"] });
  };
  const apply = useMutation({
    mutationFn: async () => { await api.POST("/api/v1/recommendations/{rec_id}/apply", { params: { path: { rec_id: rec.id } } }); },
    onSuccess: invalidate,
  });
  const reject = useMutation({
    mutationFn: async (reason: string) => { await api.POST("/api/v1/recommendations/{rec_id}/reject", { params: { path: { rec_id: rec.id } }, body: { reason_code: reason } }); },
    onSuccess: invalidate,
  });

  const p = rec.projected;
  const reasons = REJECT_REASONS[rec.type] ?? ["Not now"];

  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-card)]">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[var(--color-primary-50)] text-[var(--color-primary)]">
          <Lightbulb className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="font-medium text-[var(--color-text)]">{rec.title}</div>
          <p className="mt-0.5 text-sm text-[var(--color-text-muted)]">{rec.body}</p>
          {p?.uplift_pct != null && p.uplift_pct > 0 && (
            <span className="mt-2 inline-block rounded-full bg-[var(--color-success-50)] px-2 py-0.5 text-xs font-medium text-[var(--color-success)]">
              +{p.uplift_pct}% {p.metric}{p.current != null && p.projected != null ? ` · ${p.current} → ${p.projected}/wk` : ""}
            </span>
          )}
          {!rejecting ? (
            <div className="mt-3 flex gap-2">
              <Button size="sm" onClick={() => apply.mutate()} disabled={apply.isPending}>Apply</Button>
              <Button size="sm" variant="ghost" onClick={() => setRejecting(true)}>Reject</Button>
            </div>
          ) : (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {reasons.map((r) => (
                <button key={r} onClick={() => reject.mutate(r)} className="rounded-full border border-[var(--color-border)] px-2.5 py-1 text-xs text-[var(--color-text-body)] hover:bg-[var(--color-bg-subtle)]">
                  {r}
                </button>
              ))}
              <button onClick={() => setRejecting(false)} className="px-2 py-1 text-xs text-[var(--color-text-muted)]">Cancel</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
