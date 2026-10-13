"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { KpiTile } from "@/components/app/KpiTile";
import { PageHeader } from "@/components/app/PageHeader";
import { StatusPill } from "@/components/app/StatusPill";
import { TrendChart } from "@/components/app/TrendChart";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Select } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { goalDef } from "@/lib/campaign-config";
import { type CampaignDetail } from "@/lib/hooks";
import { nfCompact, usd } from "@/lib/utils";

const METRICS = [
  { key: "spend", label: "Spend", fmt: (v: number) => usd(v) },
  { key: "impressions", label: "Impressions", fmt: (v: number) => nfCompact.format(v) },
  { key: "households", label: "Households", fmt: (v: number) => nfCompact.format(v) },
  { key: "sessions", label: "Sessions", fmt: (v: number) => nfCompact.format(v) },
  { key: "revenue", label: "Revenue", fmt: (v: number) => usd(v) },
];

export default function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [metric, setMetric] = useState("spend");

  const { data: campaign } = useQuery({
    queryKey: ["campaign", id],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/campaigns/{campaign_id}", { params: { path: { campaign_id: id } } });
      if (error) throw error;
      return data as CampaignDetail;
    },
  });
  const { data: table } = useQuery({
    queryKey: ["stats-table", "campaign"],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/stats/table", { params: { query: { level: "campaign" } } });
      return (data as { items: Record<string, number & string>[] })?.items ?? [];
    },
  });
  const { data: ts } = useQuery({
    queryKey: ["timeseries", id, metric],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/stats/timeseries", { params: { query: { metric, campaign_id: id } } });
      return (data as { points: { date: string; value: number }[] })?.points ?? [];
    },
  });

  const sid = campaign?.strategies?.[0] ? String(campaign.strategies[0].id) : "";
  const { data: forecast } = useQuery({
    queryKey: ["forecast", sid],
    enabled: !!sid,
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/strategies/{strategy_id}/forecast", { params: { path: { strategy_id: sid } } });
      return data as {
        available: boolean; outcome_metric?: string; current_budget_micros?: number; recommended_budget_micros?: number;
        current_outcome?: number; recommended_outcome?: number; points?: { budget_micros: number; outcome: number }[];
      };
    },
  });

  const m = (table ?? []).find((r) => String(r.id) === id) as Record<string, number> | undefined;

  const action = useMutation({
    mutationFn: async (what: "pause" | "resume") => {
      const path = what === "pause" ? "/api/v1/campaigns/{campaign_id}/pause" : "/api/v1/campaigns/{campaign_id}/resume";
      await api.POST(path, { params: { path: { campaign_id: id } } });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaign", id] }),
  });
  const scale = useMutation({
    mutationFn: async (budget: number) => {
      await api.PATCH("/api/v1/strategies/{strategy_id}", { params: { path: { strategy_id: sid } }, body: { budget_micros: budget } as never });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["campaign", id] });
      qc.invalidateQueries({ queryKey: ["forecast", sid] });
    },
  });

  if (!campaign) return <div className="space-y-4 px-8 py-8" aria-busy="true" aria-label="Loading campaign"><Skeleton className="h-8 w-64" /><Skeleton className="h-40 w-full" /><Skeleton className="h-64 w-full" /></div>;

  const fmt = METRICS.find((x) => x.key === metric)?.fmt ?? ((v: number) => nfCompact.format(v));
  const learning = campaign.status === "learning";

  return (
    <>
      <PageHeader
        title={campaign.name}
        subtitle={goalDef(campaign.goal)?.label}
        action={
          <div className="flex items-center gap-2">
            <StatusPill status={campaign.status} />
            {campaign.status === "paused" ? (
              <Button variant="outline" onClick={() => action.mutate("resume")}>Resume</Button>
            ) : (
              <Button variant="outline" onClick={() => action.mutate("pause")}>Pause</Button>
            )}
            <Button asChild><Link href={`/dashboard/campaigns/${id}/edit`}>Edit</Link></Button>
          </div>
        }
      />
      <div className="space-y-6 px-8 py-8">
        {learning && (
          <div className="rounded-[var(--radius-md)] bg-[var(--color-primary-50)] px-4 py-2.5 text-sm text-[var(--color-primary)]">
            <span className="lumen-pulse mr-2 inline-block h-2 w-2 rounded-full bg-current" />
            Learning — results aren&apos;t representative yet{campaign.attribution_window_hours ? "" : ""}.
          </div>
        )}

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <KpiTile label="Spend" value={m ? usd(m.spend_micros) : "$0.00"} />
          <KpiTile label="Impressions" value={m ? nfCompact.format(m.impressions) : "0"} />
          <KpiTile label="Households" value={m ? nfCompact.format(m.households) : "0"} />
          <KpiTile label="Sessions" value={m ? nfCompact.format(m.sessions) : "0"} />
          <KpiTile label="Purchases" value={m ? nfCompact.format(m.purchases) : "0"} />
          <KpiTile label="ROAS" value={m && m.roas ? `${(m.roas as number).toFixed(2)}×` : "—"} />
        </div>

        <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-card)]">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[var(--color-text)]">Last 7 days</h3>
            <Select value={metric} onChange={(e) => setMetric(e.target.value)} className="w-40">
              {METRICS.map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}
            </Select>
          </div>
          {ts && ts.some((p) => p.value > 0) ? (
            <TrendChart points={ts} format={fmt} />
          ) : (
            <p className="py-10 text-center text-sm text-[var(--color-text-muted)]">No delivery yet — run the simulator.</p>
          )}
        </div>

        {forecast?.available && forecast.points && (
          <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-card)]">
            <h3 className="mb-1 text-sm font-semibold text-[var(--color-text)]">Performance forecaster</h3>
            <p className="mb-3 text-sm text-[var(--color-text-muted)]">
              At {usd(forecast.recommended_budget_micros ?? 0)}/day we project ~{forecast.recommended_outcome} {forecast.outcome_metric}/day
              {forecast.current_outcome ? ` (+${Math.round(((forecast.recommended_outcome ?? 0) / forecast.current_outcome - 1) * 100)}% vs current)` : ""}.
            </p>
            <TrendChart
              points={forecast.points.map((p) => ({ date: String(Math.round(p.budget_micros / 1e6)), value: p.outcome }))}
              format={(v) => nfCompact.format(v)}
              height={180}
            />
            <Button className="mt-3" onClick={() => scale.mutate(forecast.recommended_budget_micros ?? 0)} disabled={scale.isPending}>
              Scale to recommended ({usd(forecast.recommended_budget_micros ?? 0)}/day)
            </Button>
          </div>
        )}

        <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-card)]">
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-text)]">Strategies</h3>
          <ul className="space-y-2 text-sm">
            {campaign.strategies.map((s) => (
              <li key={String(s.id)} className="flex items-center justify-between rounded-[var(--radius-md)] bg-[var(--color-bg-subtle)] px-3 py-2">
                <span className="text-[var(--color-text)]">{s.name}</span>
                <span className="text-[var(--color-text-muted)]">{usd(s.budget_micros)}/{s.budget_type === "daily" ? "day" : "lifetime"}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </>
  );
}
