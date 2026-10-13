"use client";

import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { EmptyState } from "@/components/app/EmptyState";
import { PageHeader } from "@/components/app/PageHeader";
import { RecommendationCard, type Rec } from "@/components/app/RecommendationCard";
import { TrendChart } from "@/components/app/TrendChart";
import { Button } from "@/components/ui/button";
import { ARTICLES } from "@/content/help";
import { api } from "@/lib/api/client";
import { type Campaign, useMe } from "@/lib/hooks";
import { nfCompact, PRODUCT_NAME, usd } from "@/lib/utils";

const METRICS = [
  { key: "spend", label: "Spend", fmt: (v: number) => usd(v) },
  { key: "impressions", label: "Impressions", fmt: (v: number) => nfCompact.format(v) },
  { key: "households", label: "Households", fmt: (v: number) => nfCompact.format(v) },
  { key: "sessions", label: "Sessions", fmt: (v: number) => nfCompact.format(v) },
];
const STATUSES: [string, string][] = [["delivering", "Delivering"], ["learning", "Learning"], ["paused", "Paused"], ["blocked", "Blocked"], ["draft", "Draft"]];

export default function DashboardPage() {
  const { data: me } = useMe();
  const [metric, setMetric] = useState("spend");
  const firstName = me?.full_name?.split(" ")[0];

  const { data: campaigns = [] } = useQuery({
    queryKey: ["campaigns"],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/campaigns");
      return (data as Campaign[]) ?? [];
    },
  });
  const { data: ts } = useQuery({
    queryKey: ["timeseries", "dash", metric],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/stats/timeseries", { params: { query: { metric } } });
      return (data as { points: { date: string; value: number }[] })?.points ?? [];
    },
  });
  const { data: recs = [] } = useQuery({
    queryKey: ["recommendations"],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/recommendations", { params: { query: { status: "open" } } });
      return (data as Rec[]) ?? [];
    },
  });
  const { data: advertisers = [] } = useQuery({
    queryKey: ["advertisers"],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/advertisers");
      return (data as unknown[]) ?? [];
    },
  });
  const { data: pixels = [] } = useQuery({
    queryKey: ["pixels"],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/pixels");
      return (data as unknown[]) ?? [];
    },
  });

  const counts = STATUSES.map(([s, label]) => [s, label, campaigns.filter((c) => c.status === s).length] as const);
  const fmt = METRICS.find((x) => x.key === metric)?.fmt ?? ((v: number) => nfCompact.format(v));
  const hasData = ts?.some((p) => p.value > 0);

  return (
    <>
      <PageHeader
        title={firstName ? `Welcome, ${firstName}` : "Dashboard"}
        subtitle={`Welcome to ${PRODUCT_NAME}! Finish the steps below to get your first streaming campaign live.`}
        action={<Button asChild><Link href="/dashboard/campaigns/new"><Plus className="h-4 w-4" />Create campaign</Link></Button>}
      />
      <div className="grid grid-cols-1 gap-6 px-8 py-8 lg:grid-cols-12">
        <div className="space-y-6 lg:col-span-8">
          <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold text-[var(--color-text)]">Last 7 days</h2>
              <div className="flex gap-1">
                {METRICS.map((x) => (
                  <button key={x.key} onClick={() => setMetric(x.key)}
                    className={`rounded-[var(--radius-md)] px-2.5 py-1 text-xs ${metric === x.key ? "bg-[var(--color-primary-50)] text-[var(--color-primary)]" : "text-[var(--color-text-muted)]"}`}>
                    {x.label}
                  </button>
                ))}
              </div>
            </div>
            {hasData ? (
              <TrendChart points={ts!} format={fmt} />
            ) : (
              <EmptyState title="No campaign delivering yet" description="Create and publish a campaign — trends appear here once it starts delivering." />
            )}
          </div>

          {recs.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-base font-semibold text-[var(--color-text)]">Recommendations</h2>
              {recs.slice(0, 4).map((r) => <RecommendationCard key={r.id} rec={r} />)}
            </div>
          )}

          {(() => {
            const steps = [
              { done: advertisers.length > 0, label: "Add an advertiser", href: "/dashboard/settings/advertisers", cta: "Add" },
              { done: pixels.length > 0, label: "Connect your pixel", href: "/dashboard/settings/tracking/web", cta: "Set up" },
              { done: campaigns.some((c) => c.status !== "draft"), label: "Publish your first campaign", href: "/dashboard/campaigns/new", cta: "Start" },
            ];
            const pct = Math.round((steps.filter((s) => s.done).length / steps.length) * 100);
            if (pct === 100) return null;
            return (
              <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]">
                <h2 className="text-base font-semibold text-[var(--color-text)]">Get started with {PRODUCT_NAME}</h2>
                <p className="mt-1 text-sm text-[var(--color-text-muted)]">You&apos;re {pct}% closer to delivering best-in-class campaigns.</p>
                <div className="mt-2 h-2 w-full rounded-full bg-[var(--color-bg-subtle)]">
                  <div className="h-2 rounded-full bg-[var(--color-primary)]" style={{ width: `${pct}%` }} />
                </div>
                <ol className="mt-4 space-y-3 text-sm text-[var(--color-text-body)]">
                  {steps.map((s) => (
                    <li key={s.label} className="flex items-center justify-between rounded-[var(--radius-md)] bg-[var(--color-bg-subtle)] px-4 py-3">
                      <span className="flex items-center gap-2">
                        <span className={`grid h-5 w-5 place-items-center rounded-full text-xs ${s.done ? "bg-[var(--color-success)] text-white" : "border border-[var(--color-border-strong)] text-transparent"}`}>✓</span>
                        <span className={s.done ? "text-[var(--color-text-muted)] line-through" : ""}>{s.label}</span>
                      </span>
                      {!s.done && <Link href={s.href} className="font-medium text-[var(--color-primary)]">{s.cta} →</Link>}
                    </li>
                  ))}
                </ol>
              </div>
            );
          })()}
        </div>

        <div className="space-y-6 lg:col-span-4">
          <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]">
            <h2 className="text-base font-semibold text-[var(--color-text)]">Campaigns</h2>
            <ul className="mt-3 space-y-1.5 text-sm">
              {counts.map(([s, label, n]) => (
                <li key={s}>
                  <Link href={`/dashboard/campaigns`} className="flex items-center justify-between rounded-[var(--radius-md)] px-3 py-2 hover:bg-[var(--color-bg-subtle)]">
                    <span className="text-[var(--color-text-body)]">{label}</span>
                    <span className="rounded-full bg-[var(--color-bg-subtle)] px-2 py-0.5 text-xs font-medium tabular-nums text-[var(--color-text-body)]">{n}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]">
            <h2 className="text-base font-semibold text-[var(--color-text)]">Learn</h2>
            <ul className="mt-3 space-y-2 text-sm">
              {ARTICLES.slice(0, 4).map((a) => (
                <li key={a.slug}>
                  <Link href={`/help/${a.slug}`} className="flex items-center justify-between text-[var(--color-text-body)] hover:text-[var(--color-primary)]">
                    <span>{a.title}</span>
                    <span className="text-xs text-[var(--color-text-muted)]">{a.readMins} min</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </>
  );
}
