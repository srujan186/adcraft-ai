"use client";

import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/app/EmptyState";
import { PageHeader } from "@/components/app/PageHeader";
import { StatusPill } from "@/components/app/StatusPill";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import { goalDef } from "@/lib/campaign-config";
import { type Campaign } from "@/lib/hooks";
import { nfCompact, usd } from "@/lib/utils";

interface Metrics {
  id: string; impressions: number; households: number; spend_micros: number;
  sessions: number; leads: number; purchases: number; installs: number;
  revenue_micros: number; roas: number;
}

export default function CampaignsPage() {
  const { data: campaigns = [], isLoading } = useQuery({
    queryKey: ["campaigns"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/campaigns");
      if (error) throw error;
      return data as Campaign[];
    },
  });
  const { data: stats } = useQuery({
    queryKey: ["stats-table", "campaign"],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/stats/table", { params: { query: { level: "campaign" } } });
      return (data as { items: Metrics[] })?.items ?? [];
    },
  });
  const byId = new Map((stats ?? []).map((m) => [m.id, m]));

  return (
    <>
      <PageHeader
        title="Campaigns"
        subtitle="See how your campaigns perform."
        action={<Button asChild><Link href="/dashboard/campaigns/new"><Plus className="h-4 w-4" />Create campaign</Link></Button>}
      />
      <div className="px-8 py-8">
        {isLoading ? (
          <p className="text-sm text-[var(--color-text-muted)]">Loading…</p>
        ) : campaigns.length === 0 ? (
          <EmptyState title="No campaigns yet" description="Create your first streaming-TV campaign to start reaching households."
            action={<Button asChild><Link href="/dashboard/campaigns/new">Create campaign</Link></Button>} />
        ) : (
          <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-[var(--color-border)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-bg-subtle)] text-left text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                <tr>
                  <th className="px-4 py-2.5 font-semibold">Campaign</th>
                  <th className="px-4 py-2.5 font-semibold">Status</th>
                  <th className="px-4 py-2.5 font-semibold">Goal</th>
                  <th className="px-4 py-2.5 text-right font-semibold">Spend</th>
                  <th className="px-4 py-2.5 text-right font-semibold">Impr.</th>
                  <th className="px-4 py-2.5 text-right font-semibold">Households</th>
                  <th className="px-4 py-2.5 text-right font-semibold">Sessions</th>
                  <th className="px-4 py-2.5 text-right font-semibold">ROAS</th>
                  <th className="px-4 py-2.5" />
                </tr>
              </thead>
              <tbody>
                {campaigns.map((c) => {
                  const m = byId.get(String(c.id));
                  return (
                    <tr key={String(c.id)} className="border-t border-[var(--color-border)]">
                      <td className="px-4 py-3 font-medium text-[var(--color-text)]">
                        <Link href={`/dashboard/campaigns/${c.id}`} className="hover:underline">{c.name}</Link>
                      </td>
                      <td className="px-4 py-3"><StatusPill status={c.status} /></td>
                      <td className="px-4 py-3 text-[var(--color-text-muted)]">{goalDef(c.goal)?.label ?? c.goal}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{m ? usd(m.spend_micros) : "—"}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text-muted)]">{m ? nfCompact.format(m.impressions) : "—"}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text-muted)]">{m ? nfCompact.format(m.households) : "—"}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text-muted)]">{m ? nfCompact.format(m.sessions) : "—"}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{m && m.roas ? `${m.roas.toFixed(2)}×` : "—"}</td>
                      <td className="px-4 py-3 text-right">
                        <Link href={`/dashboard/campaigns/${c.id}/edit`} className="text-sm font-medium text-[var(--color-primary)]">Edit →</Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
