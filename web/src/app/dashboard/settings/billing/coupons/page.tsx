"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { PageHeader } from "@/components/app/PageHeader";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { errorMessage } from "@/lib/hooks";
import { usd } from "@/lib/utils";

export default function CouponsPage() {
  const qc = useQueryClient();
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const redeem = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/v1/billing/coupons/redeem", { body: { code } });
      if (error) throw error;
      return data as { amount_micros: number };
    },
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ["balance"] });
      qc.invalidateQueries({ queryKey: ["transactions"] });
      setMsg({ ok: true, text: `Applied ${usd(d.amount_micros)} credit to your balance.` });
      setCode("");
    },
    onError: (e) => setMsg({ ok: false, text: errorMessage(e, "Invalid coupon.") }),
  });

  return (
    <>
      <PageHeader title="Coupons" subtitle="Redeem a coupon code." />
      <div className="max-w-[520px] px-8 py-8">
        <form onSubmit={(e) => { e.preventDefault(); redeem.mutate(); }} className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]">
          <Field label="Coupon code" htmlFor="coupon">
            <Input id="coupon" value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="WELCOME50" />
          </Field>
          <Button className="mt-4" type="submit" disabled={redeem.isPending || !code}>{redeem.isPending ? "Redeeming…" : "Redeem"}</Button>
          {msg && <p className={`mt-3 text-sm ${msg.ok ? "text-[var(--color-success)]" : "text-[var(--color-danger)]"}`}>{msg.text}</p>}
        </form>
      </div>
    </>
  );
}
