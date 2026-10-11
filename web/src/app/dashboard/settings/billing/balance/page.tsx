"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { PageHeader } from "@/components/app/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { errorMessage } from "@/lib/hooks";
import { usd } from "@/lib/utils";

const PRESETS = [250, 500, 1000];
interface Txn { id: string; type: string; amount_micros: number; balance_after_micros: number; created_at: string }

export default function BalancePage() {
  const qc = useQueryClient();
  const [amount, setAmount] = useState(500);
  const [error, setError] = useState<string | null>(null);

  const { data: balance } = useQuery({
    queryKey: ["balance"],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/billing/balance");
      return data as { balance_micros: number };
    },
  });
  const { data: txns = [] } = useQuery({
    queryKey: ["transactions"],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/billing/transactions");
      return (data as Txn[]) ?? [];
    },
  });

  const topup = useMutation({
    mutationFn: async () => {
      const { error } = await api.POST("/api/v1/billing/topup", { body: { amount_micros: amount * 1_000_000 } });
      if (error) throw error;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["balance"] });
      qc.invalidateQueries({ queryKey: ["transactions"] });
      setError(null);
    },
    onError: (e) => setError(errorMessage(e, "Top-up failed.")),
  });

  return (
    <>
      <PageHeader title="Balance & transactions" subtitle="Top up your balance and review spend." />
      <div className="max-w-[820px] space-y-6 px-8 py-8">
        <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]">
          <div className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">Current balance</div>
          <div className="mt-1 text-3xl font-bold tabular-nums text-[var(--color-text)]">
            {usd(balance?.balance_micros ?? 0)}
          </div>
          <div className="mt-5 flex flex-wrap items-center gap-2">
            {PRESETS.map((p) => (
              <button
                key={p}
                onClick={() => setAmount(p)}
                className={`rounded-[var(--radius-md)] border px-4 py-2 text-sm ${amount === p ? "border-[var(--color-primary)] bg-[var(--color-primary-50)] text-[var(--color-primary)]" : "border-[var(--color-border)]"}`}
              >
                ${p}
              </button>
            ))}
            <Input type="number" value={amount} onChange={(e) => setAmount(Number(e.target.value))} className="w-28" />
            <Button onClick={() => topup.mutate()} disabled={topup.isPending}>
              {topup.isPending ? "Adding…" : "Add funds"}
            </Button>
          </div>
          <p className="mt-2 text-xs text-[var(--color-text-muted)]">Test mode — no real card is charged.</p>
          {error && <p className="mt-2 text-sm text-[var(--color-danger)]">{error}</p>}
        </div>

        <div className="overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)]">
          <table className="w-full text-sm">
            <thead className="bg-[var(--color-bg-subtle)] text-left text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Date</th>
                <th className="px-4 py-2.5 font-semibold">Type</th>
                <th className="px-4 py-2.5 font-semibold">Amount</th>
                <th className="px-4 py-2.5 font-semibold">Balance after</th>
              </tr>
            </thead>
            <tbody>
              {txns.length === 0 ? (
                <tr><td colSpan={4} className="px-4 py-4 text-[var(--color-text-muted)]">No transactions yet.</td></tr>
              ) : (
                txns.map((t) => (
                  <tr key={t.id} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3 text-[var(--color-text-muted)]">{new Date(t.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3 capitalize">{t.type.replace(/_/g, " ")}</td>
                    <td className={`px-4 py-3 tabular-nums ${t.amount_micros < 0 ? "text-[var(--color-danger)]" : "text-[var(--color-success)]"}`}>
                      {t.amount_micros < 0 ? "-" : "+"}{usd(Math.abs(t.amount_micros))}
                    </td>
                    <td className="px-4 py-3 tabular-nums text-[var(--color-text-body)]">{usd(t.balance_after_micros)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
