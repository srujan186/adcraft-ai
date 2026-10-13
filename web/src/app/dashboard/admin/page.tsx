"use client";

import { useMutation } from "@tanstack/react-query";
import { notFound } from "next/navigation";
import { useState } from "react";

import { PageHeader } from "@/components/app/PageHeader";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/client";
import { errorMessage, useAdminStatus } from "@/lib/hooks";

const card = "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]";

/** Platform admin tools for demos. The API answers 404 unless ALLOW_SIMULATION=true and the
 * user is in ADMIN_EMAILS, so everyone else gets the not-found page. */
export default function AdminPage() {
  const { data: status, isError } = useAdminStatus();
  const [days, setDays] = useState(30);
  const [password, setPassword] = useState("");
  const [notice, setNotice] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  const simulate = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/v1/admin/simulate", { body: { days } });
      if (error) throw error;
      return data;
    },
    onSuccess: () => setNotice({ kind: "ok", text: `Adding ${days} days of delivery history to this account. Dashboards update within a minute or two.` }),
    onError: (e) => setNotice({ kind: "error", text: errorMessage(e, "Couldn't start the simulation.") }),
  });

  const reset = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/v1/admin/demo-reset", { body: { password } });
      if (error) throw error;
      return data as { email: string };
    },
    onSuccess: (d) => {
      setPassword("");
      setNotice({ kind: "ok", text: `Rebuilding the demo account. In a few minutes, log in as ${d.email} with the password you set.` });
    },
    onError: (e) => setNotice({ kind: "error", text: errorMessage(e, "Couldn't reset the demo account.") }),
  });

  if (isError) notFound();

  return (
    <>
      <PageHeader title="Admin" subtitle="Demo and delivery tools. Only platform admins can see this page." />
      <div className="max-w-[820px] space-y-6 px-8 py-8">
        {notice && (
          <p role="status" id="admin-notice"
             className={`rounded-[var(--radius-md)] px-4 py-3 text-sm ${notice.kind === "ok"
               ? "bg-[var(--color-success-50)] text-[var(--color-text-body)]"
               : "bg-[var(--color-danger-50)] text-[var(--color-danger)]"}`}>
            {notice.text}
          </p>
        )}

        <section className={card}>
          <h2 className="text-base font-semibold text-[var(--color-text)]">Delivery</h2>
          {status ? (
            <dl className="mt-3 grid grid-cols-3 gap-4 text-sm">
              <div><dt className="text-[var(--color-text-muted)]">Continuous delivery</dt>
                <dd className="font-medium text-[var(--color-text)]">{status.delivery_loop ? "On" : "Off"}</dd></div>
              <div><dt className="text-[var(--color-text-muted)]">Speed</dt>
                <dd className="font-medium text-[var(--color-text)]">{status.sim_speed === 1 ? "Real time" : `${status.sim_speed}× real time`}</dd></div>
              <div><dt className="text-[var(--color-text-muted)]">Runs every</dt>
                <dd className="font-medium text-[var(--color-text)]">{Math.round(status.tick_seconds / 60)} min</dd></div>
            </dl>
          ) : (
            <Skeleton className="mt-3 h-10 w-full" />
          )}
        </section>

        <form className={card} onSubmit={(e) => { e.preventDefault(); simulate.mutate(); }}>
          <h2 className="text-base font-semibold text-[var(--color-text)]">Add delivery history</h2>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Backfills past days for this account&apos;s live campaigns only — never other customers&apos;.
          </p>
          <div className="mt-4 flex items-end gap-3">
            <div className="w-40">
              <Field label="Days" htmlFor="admin-days">
                <Input id="admin-days" type="number" min={1} max={60} value={days}
                       onChange={(e) => setDays(Math.max(1, Math.min(60, Number(e.target.value) || 1)))} />
              </Field>
            </div>
            <Button type="submit" disabled={simulate.isPending} id="admin-simulate">Simulate history</Button>
          </div>
        </form>

        <form className={card} onSubmit={(e) => { e.preventDefault(); if (password.length >= 8) reset.mutate(); }}>
          <h2 className="text-base font-semibold text-[var(--color-text)]">Demo account</h2>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Replaces “Demo Co” with a fresh copy: one advertiser, three live campaigns and 30 days of results.
          </p>
          <div className="mt-4 flex items-end gap-3">
            <div className="flex-1">
              <Field label="New password for the demo login" htmlFor="admin-demo-password">
                <Input id="admin-demo-password" type="password" minLength={8} value={password}
                       onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
              </Field>
            </div>
            <Button type="submit" disabled={reset.isPending || password.length < 8} id="admin-reset">Reset demo account</Button>
          </div>
        </form>
      </div>
    </>
  );
}
