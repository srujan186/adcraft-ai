"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { KpiTile } from "@/components/app/KpiTile";
import { PageHeader } from "@/components/app/PageHeader";
import { Select } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { type Advertiser } from "@/lib/hooks";

interface Check { have: number; need: number; ok: boolean }
interface Inc { eligible: boolean; checks: Record<string, Check>; result: { lift_pct: number; incremental_conversions: number } | null }

const LABELS: Record<string, string> = { days: "Days of delivery", spend: "Spend ($)", conversions: "Attributed conversions", holdout: "Holdout households" };

export default function IncrementalityPage() {
  const [adv, setAdv] = useState("");
  const { data: advertisers = [] } = useQuery({
    queryKey: ["advertisers"],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/advertisers");
      return (data as Advertiser[]) ?? [];
    },
  });
  const advId = adv || (advertisers[0] ? String(advertisers[0].id) : "");

  const { data } = useQuery({
    queryKey: ["incrementality", advId],
    enabled: !!advId,
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/insights/incrementality", { params: { query: { advertiser_id: advId } } });
      return data as Inc;
    },
  });

  return (
    <>
      <PageHeader
        title="Insights"
        subtitle="Campaign performance and incremental impact across your account."
        action={
          <Select value={advId} onChange={(e) => setAdv(e.target.value)} className="w-56">
            {advertisers.map((a) => <option key={String(a.id)} value={String(a.id)}>{a.name}</option>)}
          </Select>
        }
      />
      <div className="border-b border-[var(--color-border)] px-8">
        <nav className="flex gap-6 text-sm">
          <Link href="/dashboard/insights/overview" className="py-2 text-[var(--color-text-muted)]">Overview</Link>
          <span className="border-b-2 border-[var(--color-primary)] py-2 font-medium text-[var(--color-text)]">Incrementality</span>
        </nav>
      </div>

      <div className="max-w-[720px] px-8 py-8">
        {!data ? (
          <p className="text-sm text-[var(--color-text-muted)]">Loading…</p>
        ) : data.eligible && data.result ? (
          <div className="space-y-6">
            <p className="text-sm text-[var(--color-text-muted)]">Measured against a held-out control group.</p>
            <div className="grid grid-cols-2 gap-4">
              <KpiTile label="Incremental lift" value={`${data.result.lift_pct}%`} />
              <KpiTile label="Incremental conversions" value={String(data.result.incremental_conversions)} />
            </div>
          </div>
        ) : (
          <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]">
            <h2 className="text-base font-semibold text-[var(--color-text)]">Incrementality unlocks automatically</h2>
            <p className="mt-1 text-sm text-[var(--color-text-muted)]">
              Once this advertiser meets the eligibility thresholds, lift measurement appears here.
            </p>
            <ul className="mt-5 space-y-3">
              {Object.entries(data.checks).map(([k, c]) => (
                <li key={k}>
                  <div className="flex justify-between text-sm">
                    <span className="text-[var(--color-text-body)]">{LABELS[k] ?? k}</span>
                    <span className={`tabular-nums ${c.ok ? "text-[var(--color-success)]" : "text-[var(--color-text-muted)]"}`}>
                      {c.have} / {c.need} {c.ok ? "✓" : ""}
                    </span>
                  </div>
                  <div className="mt-1 h-2 w-full rounded-full bg-[var(--color-bg-subtle)]">
                    <div className={`h-2 rounded-full ${c.ok ? "bg-[var(--color-success)]" : "bg-[var(--color-primary)]"}`}
                      style={{ width: `${Math.min(100, (c.have / c.need) * 100)}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </>
  );
}
