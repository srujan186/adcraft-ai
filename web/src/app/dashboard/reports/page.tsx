"use client";

import { useMutation } from "@tanstack/react-query";
import { Download, Play } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/app/PageHeader";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import { nfCompact, usd } from "@/lib/utils";

const DIMENSIONS: [string, string][] = [
  ["date", "Date"], ["campaign", "Campaign"], ["strategy", "Strategy"],
  ["creative", "Creative"], ["channel", "Channel"], ["region", "Region (State)"],
];
const METRICS: { key: string; label: string; micros?: boolean; ratio?: boolean }[] = [
  { key: "spend", label: "Spend", micros: true },
  { key: "impressions", label: "Impressions" },
  { key: "households", label: "Households" },
  { key: "frequency", label: "Frequency", ratio: true },
  { key: "cpm", label: "CPM", micros: true },
  { key: "sessions", label: "Sessions" },
  { key: "cps", label: "Cost per session", micros: true },
  { key: "leads", label: "Leads" },
  { key: "purchases", label: "Purchases" },
  { key: "cpp", label: "Cost per purchase", micros: true },
  { key: "revenue", label: "Revenue", micros: true },
  { key: "roas", label: "ROAS", ratio: true },
];

export default function ReportsPage() {
  const [dims, setDims] = useState<string[]>(["date", "channel"]);
  const [mets, setMets] = useState<string[]>(["impressions", "spend", "sessions"]);
  const [rows, setRows] = useState<Record<string, number | string>[] | null>(null);

  const run = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/v1/reports/run", {
        body: { dimensions: dims, metrics: mets, filters: {}, date_range: {} } as never,
      });
      if (error) throw error;
      return (data as { rows: Record<string, number | string>[] }).rows;
    },
    onSuccess: (r) => setRows(r),
  });

  const toggle = (set: (f: (p: string[]) => string[]) => void, key: string) =>
    set((p) => (p.includes(key) ? p.filter((x) => x !== key) : [...p, key]));

  const cols = [...dims, ...mets];
  const fmt = (k: string, v: number | string) => {
    const meta = METRICS.find((m) => m.key === k);
    if (meta?.micros) return usd(Number(v));
    if (meta?.ratio) return k === "roas" ? `${Number(v).toFixed(2)}×` : Number(v).toFixed(2);
    if (typeof v === "number") return nfCompact.format(v);
    return String(v ?? "—");
  };

  function downloadCsv() {
    if (!rows) return;
    const header = cols.join(",");
    const lines = rows.map((r) => cols.map((c) => r[c] ?? "").join(","));
    const blob = new Blob([[header, ...lines].join("\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "report.csv";
    a.click();
  }

  return (
    <>
      <PageHeader
        title="Reports"
        subtitle="Create a report to analyze your data."
        action={
          <div className="flex gap-2">
            {rows && <Button variant="outline" onClick={downloadCsv}><Download className="h-4 w-4" />CSV</Button>}
            <Button onClick={() => run.mutate()} disabled={run.isPending || mets.length === 0}><Play className="h-4 w-4" />Run</Button>
          </div>
        }
      />
      <div className="grid grid-cols-12 gap-6 px-8 py-8">
        <aside className="col-span-12 space-y-5 lg:col-span-3">
          <Group title="Dimensions">
            {DIMENSIONS.map(([k, label]) => (
              <Check key={k} label={label} checked={dims.includes(k)} onChange={() => toggle(setDims, k)} />
            ))}
          </Group>
          <Group title="Metrics">
            {METRICS.map((m) => (
              <Check key={m.key} label={m.label} checked={mets.includes(m.key)} onChange={() => toggle(setMets, m.key)} />
            ))}
          </Group>
        </aside>
        <main className="col-span-12 lg:col-span-9">
          {!rows ? (
            <div className="grid place-items-center rounded-[var(--radius-lg)] border border-dashed border-[var(--color-border-strong)] bg-[var(--color-bg-subtle)] py-24 text-center text-sm text-[var(--color-text-muted)]">
              Select metrics and dimensions, then click Run.
            </div>
          ) : rows.length === 0 ? (
            <div className="grid place-items-center rounded-[var(--radius-lg)] border border-[var(--color-border)] py-24 text-sm text-[var(--color-text-muted)]">
              No data for the selected dates. Results appear once a campaign is live and delivering.
            </div>
          ) : (
            <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-[var(--color-border)]">
              <table className="w-full text-sm">
                <thead className="bg-[var(--color-bg-subtle)] text-left text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                  <tr>{cols.map((c) => <th key={c} className="px-4 py-2.5 font-semibold">{c.replace(/_/g, " ")}</th>)}</tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i} className="border-t border-[var(--color-border)]">
                      {cols.map((c) => <td key={c} className="px-4 py-2.5 tabular-nums">{fmt(c, r[c])}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </main>
      </div>
    </>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-card)]">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">{title}</p>
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}

function Check({ label, checked, onChange }: { label: string; checked: boolean; onChange: () => void }) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-sm text-[var(--color-text-body)]">
      <input type="checkbox" checked={checked} onChange={onChange} />
      {label}
    </label>
  );
}
