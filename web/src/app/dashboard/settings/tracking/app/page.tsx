"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/components/app/EmptyState";
import { PageHeader } from "@/components/app/PageHeader";
import { StatusPill } from "@/components/app/StatusPill";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { type Advertiser, errorMessage } from "@/lib/hooks";

const MMPS = ["appsflyer", "adjust", "branch", "kochava", "singular", "airbridge", "gamesight"];
interface AppRow { id: string; platform: string; mmp: string; status: string; postback_url: string | null; store_url: string | null }

export default function AppTrackingPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ advertiser_id: "", platform: "ios", mmp: "appsflyer", store_url: "", bundle_id: "" });
  const [error, setError] = useState<string | null>(null);

  const { data: advertisers = [] } = useQuery({
    queryKey: ["advertisers"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/advertisers");
      if (error) throw error;
      return data as Advertiser[];
    },
  });
  const { data: apps = [] } = useQuery({
    queryKey: ["apps"],
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/apps");
      return (data as AppRow[]) ?? [];
    },
  });

  const create = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/v1/apps", {
        body: {
          advertiser_id: (form.advertiser_id || advertisers[0]?.id || "") as string,
          platform: form.platform as never,
          mmp: form.mmp as never,
          store_url: form.store_url || null,
          bundle_id: form.bundle_id || null,
        },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["apps"] });
      setOpen(false);
      setError(null);
    },
    onError: (e) => setError(errorMessage(e, "Could not add app.")),
  });

  const noAdv = advertisers.length === 0;

  return (
    <>
      <PageHeader
        title="App Tracking"
        subtitle="Connect your MMP to measure installs."
        action={<Button onClick={() => setOpen((v) => !v)} disabled={noAdv}><Plus className="h-4 w-4" />Add app</Button>}
      />
      <div className="max-w-[820px] px-8 py-8">
        {noAdv && (
          <p className="mb-4 rounded-[var(--radius-md)] bg-[var(--color-warning-50)] px-4 py-2 text-sm text-[var(--color-warning)]">
            Add an advertiser first (Settings → Advertisers).
          </p>
        )}
        {open && !noAdv && (
          <form
            onSubmit={(e) => { e.preventDefault(); create.mutate(); }}
            className="mb-6 grid gap-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)] sm:grid-cols-2"
          >
            <Field label="Advertiser" htmlFor="a-adv">
              <Select id="a-adv" value={form.advertiser_id} onChange={(e) => setForm({ ...form, advertiser_id: e.target.value })}>
                {advertisers.map((a) => <option key={String(a.id)} value={String(a.id)}>{a.name}</option>)}
              </Select>
            </Field>
            <Field label="Platform" htmlFor="a-plat">
              <Select id="a-plat" value={form.platform} onChange={(e) => setForm({ ...form, platform: e.target.value })}>
                <option value="ios">iOS</option>
                <option value="android">Android</option>
              </Select>
            </Field>
            <Field label="MMP" htmlFor="a-mmp">
              <Select id="a-mmp" value={form.mmp} onChange={(e) => setForm({ ...form, mmp: e.target.value })}>
                {MMPS.map((m) => <option key={m} value={m}>{m}</option>)}
              </Select>
            </Field>
            <Field label="Store URL" htmlFor="a-store">
              <Input id="a-store" value={form.store_url} onChange={(e) => setForm({ ...form, store_url: e.target.value })} />
            </Field>
            {error && <p className="text-sm text-[var(--color-danger)] sm:col-span-2">{error}</p>}
            <div className="sm:col-span-2">
              <Button type="submit" disabled={create.isPending}>{create.isPending ? "Adding…" : "Add app"}</Button>
            </div>
          </form>
        )}

        {apps.length === 0 ? (
          <EmptyState title="No apps connected" description="Add your mobile app and connect your MMP to measure installs and in-app revenue." />
        ) : (
          <div className="space-y-3">
            {apps.map((a) => (
              <div key={a.id} className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-card)]">
                <div className="flex items-center justify-between">
                  <div className="font-medium text-[var(--color-text)]">{a.platform.toUpperCase()} · {a.mmp}</div>
                  <StatusPill status={a.status === "connected" ? "delivering" : "draft"} />
                </div>
                <p className="mt-2 text-xs text-[var(--color-text-muted)]">Postback URL (configure in your MMP):</p>
                <pre className="mt-1 overflow-x-auto rounded-[var(--radius-md)] bg-[var(--color-bg-subtle)] p-2 text-xs">{a.postback_url}</pre>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
