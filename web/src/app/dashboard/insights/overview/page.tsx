"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { EmptyState } from "@/components/app/EmptyState";
import { PageHeader } from "@/components/app/PageHeader";
import { Select } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { type Advertiser } from "@/lib/hooks";
import { nfCompact, usd } from "@/lib/utils";

interface Overview {
  geo: { state: string; impressions: number; spend_micros: number; sessions: number; revenue_micros: number }[];
  inventory: { channel: string; impressions: number; spend_micros: number; sessions: number; roas: number }[];
  creative: { creative: string; impressions: number; sessions: number; purchases: number; roas: number }[];
  demographics: { age: string; gender: string; impressions: number }[];
  interests: { interest: string; impressions: number }[];
}

function Bar({ value, max }: { value: number; max: number }) {
  return (
    <div className="h-2 w-full rounded-full bg-[var(--color-bg-subtle)]">
      <div className="h-2 rounded-full bg-[var(--color-primary)]" style={{ width: `${max ? (value / max) * 100 : 0}%` }} />
    </div>
  );
}

export default function InsightsOverviewPage() {
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
    queryKey: ["insights", advId],
    enabled: !!advId,
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/insights/overview", { params: { query: { advertiser_id: advId } } });
      return data as Overview;
    },
  });

  const hasData = data && (data.geo.length > 0 || data.inventory.length > 0);
  const maxGeo = Math.max(1, ...(data?.geo ?? []).map((g) => g.impressions));
  const maxInt = Math.max(1, ...(data?.interests ?? []).map((i) => i.impressions));

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
          <span className="border-b-2 border-[var(--color-primary)] py-2 font-medium text-[var(--color-text)]">Overview</span>
          <Link href="/dashboard/insights/incrementality" className="py-2 text-[var(--color-text-muted)]">Incrementality</Link>
        </nav>
      </div>

      <div className="px-8 py-8">
        {!hasData ? (
          <EmptyState title="No data available for the selected dates" description="Insights appear here once a campaign for this advertiser is live and delivering." />
        ) : (
          <div className="grid gap-6 lg:grid-cols-2">
            <Card title="Geographic (by state)">
              <div className="space-y-2">
                {data!.geo.sort((a, b) => b.impressions - a.impressions).slice(0, 12).map((g) => (
                  <div key={g.state} className="flex items-center gap-3 text-sm">
                    <span className="w-8 font-medium text-[var(--color-text)]">{g.state}</span>
                    <Bar value={g.impressions} max={maxGeo} />
                    <span className="w-16 text-right tabular-nums text-[var(--color-text-muted)]">{nfCompact.format(g.impressions)}</span>
                  </div>
                ))}
              </div>
            </Card>

            <Card title="Inventory (top channels)">
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase text-[var(--color-text-muted)]">
                  <tr><th className="py-1">Channel</th><th className="py-1 text-right">Impr.</th><th className="py-1 text-right">Spend</th><th className="py-1 text-right">ROAS</th></tr>
                </thead>
                <tbody>
                  {data!.inventory.slice(0, 10).map((c) => (
                    <tr key={c.channel} className="border-t border-[var(--color-border)]">
                      <td className="py-1.5">{c.channel}</td>
                      <td className="py-1.5 text-right tabular-nums text-[var(--color-text-muted)]">{nfCompact.format(c.impressions)}</td>
                      <td className="py-1.5 text-right tabular-nums">{usd(c.spend_micros)}</td>
                      <td className="py-1.5 text-right tabular-nums">{c.roas ? `${c.roas.toFixed(2)}×` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>

            <Card title="Demographics (impressions)">
              <div className="space-y-1.5">
                {data!.demographics.sort((a, b) => b.impressions - a.impressions).slice(0, 12).map((d, i) => (
                  <div key={i} className="flex items-center gap-3 text-sm">
                    <span className="w-28 text-[var(--color-text-body)]">{d.age} · {d.gender}</span>
                    <Bar value={d.impressions} max={Math.max(1, ...data!.demographics.map((x) => x.impressions))} />
                    <span className="w-16 text-right tabular-nums text-[var(--color-text-muted)]">{nfCompact.format(d.impressions)}</span>
                  </div>
                ))}
              </div>
            </Card>

            <Card title="In-market & interests">
              <div className="space-y-1.5">
                {data!.interests.slice(0, 12).map((it) => (
                  <div key={it.interest} className="flex items-center gap-3 text-sm">
                    <span className="w-40 truncate text-[var(--color-text-body)]" title={it.interest}>{it.interest}</span>
                    <Bar value={it.impressions} max={maxInt} />
                  </div>
                ))}
              </div>
            </Card>

            <Card title="Creative">
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase text-[var(--color-text-muted)]">
                  <tr><th className="py-1">Creative</th><th className="py-1 text-right">Impr.</th><th className="py-1 text-right">Sessions</th><th className="py-1 text-right">ROAS</th></tr>
                </thead>
                <tbody>
                  {data!.creative.map((c) => (
                    <tr key={c.creative} className="border-t border-[var(--color-border)]">
                      <td className="py-1.5">{c.creative}</td>
                      <td className="py-1.5 text-right tabular-nums text-[var(--color-text-muted)]">{nfCompact.format(c.impressions)}</td>
                      <td className="py-1.5 text-right tabular-nums text-[var(--color-text-muted)]">{nfCompact.format(c.sessions)}</td>
                      <td className="py-1.5 text-right tabular-nums">{c.roas ? `${c.roas.toFixed(2)}×` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>
        )}
      </div>
    </>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-card)]">
      <h3 className="mb-3 text-sm font-semibold text-[var(--color-text)]">{title}</h3>
      {children}
    </section>
  );
}
