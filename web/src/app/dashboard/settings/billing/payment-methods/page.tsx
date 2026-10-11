"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CreditCard, Plus } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/components/app/EmptyState";
import { PageHeader } from "@/components/app/PageHeader";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { errorMessage } from "@/lib/hooks";

interface PM { id: string; brand: string; last4: string; exp_month: number; exp_year: number; is_default: boolean }

export default function PaymentMethodsPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ number: "4242424242424242", exp_month: 12, exp_year: 2030 });
  const [error, setError] = useState<string | null>(null);

  const { data: methods = [] } = useQuery({
    queryKey: ["payment-methods"],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/billing/payment-methods");
      return (data as PM[]) ?? [];
    },
  });

  const add = useMutation({
    mutationFn: async () => {
      const { error } = await api.POST("/api/v1/billing/payment-methods", {
        body: { number: form.number, exp_month: form.exp_month, exp_year: form.exp_year, is_default: true },
      });
      if (error) throw error;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["payment-methods"] }); setOpen(false); setError(null); },
    onError: (e) => setError(errorMessage(e, "Could not add card.")),
  });

  return (
    <>
      <PageHeader title="Payment methods" subtitle="Manage the cards on file." action={<Button onClick={() => setOpen((v) => !v)}><Plus className="h-4 w-4" />Add card</Button>} />
      <div className="max-w-[640px] space-y-4 px-8 py-8">
        {open && (
          <form onSubmit={(e) => { e.preventDefault(); add.mutate(); }} className="grid gap-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)] sm:grid-cols-2">
            <Field label="Card number (test 4242…)" htmlFor="c-num">
              <Input id="c-num" value={form.number} onChange={(e) => setForm({ ...form, number: e.target.value })} />
            </Field>
            <div className="grid grid-cols-2 gap-2">
              <Field label="Exp month" htmlFor="c-mm"><Input id="c-mm" type="number" value={form.exp_month} onChange={(e) => setForm({ ...form, exp_month: Number(e.target.value) })} /></Field>
              <Field label="Exp year" htmlFor="c-yy"><Input id="c-yy" type="number" value={form.exp_year} onChange={(e) => setForm({ ...form, exp_year: Number(e.target.value) })} /></Field>
            </div>
            {error && <p className="text-sm text-[var(--color-danger)] sm:col-span-2">{error}</p>}
            <div className="sm:col-span-2"><Button type="submit" disabled={add.isPending}>{add.isPending ? "Adding…" : "Add card"}</Button></div>
          </form>
        )}
        {methods.length === 0 ? (
          <EmptyState title="No cards on file" description="Add a card to top up your balance (test mode)." />
        ) : (
          methods.map((m) => (
            <div key={m.id} className="flex items-center gap-3 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-card)]">
              <CreditCard className="h-5 w-5 text-[var(--color-text-muted)]" />
              <div className="text-sm">
                <span className="font-medium text-[var(--color-text)]">{m.brand} •••• {m.last4}</span>
                <span className="ml-2 text-[var(--color-text-muted)]">exp {m.exp_month}/{m.exp_year}</span>
              </div>
              {m.is_default && <span className="ml-auto rounded-full bg-[var(--color-primary-50)] px-2 py-0.5 text-xs text-[var(--color-primary)]">Default</span>}
            </div>
          ))
        )}
      </div>
    </>
  );
}
