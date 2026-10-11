"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/components/app/EmptyState";
import { PageHeader } from "@/components/app/PageHeader";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { type Advertiser, errorMessage } from "@/lib/hooks";

const INDUSTRIES: [string, string][] = [
  ["ecommerce", "E-commerce"],
  ["retail", "Retail"],
  ["apps_gaming", "Apps & Gaming"],
  ["b2b", "B2B / SaaS"],
  ["finance", "Finance"],
  ["health_wellness", "Health & Wellness"],
  ["travel", "Travel"],
  ["food_bev", "Food & Beverage"],
  ["automotive", "Automotive"],
  ["media_entertainment", "Media & Entertainment"],
  ["education_nonprofit", "Education / Nonprofit"],
  ["home_improvement", "Home Improvement"],
  ["legal", "Legal"],
  ["politics", "Politics"],
  ["other", "Other"],
];

export default function AdvertisersSettingsPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", website_url: "", industry: "other" });
  const [error, setError] = useState<string | null>(null);

  const { data: advertisers = [], isLoading } = useQuery({
    queryKey: ["advertisers"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/advertisers");
      if (error) throw error;
      return data as Advertiser[];
    },
  });

  const create = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/v1/advertisers", {
        body: {
          name: form.name,
          website_url: form.website_url || null,
          industry: form.industry as Advertiser["industry"],
          timezone: "America/New_York",
        },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["advertisers"] });
      setForm({ name: "", website_url: "", industry: "other" });
      setOpen(false);
      setError(null);
    },
    onError: (e) => setError(errorMessage(e, "Could not create advertiser.")),
  });

  return (
    <>
      <PageHeader
        title="Advertisers"
        subtitle="Manage the brands you advertise."
        action={
          <Button onClick={() => setOpen((v) => !v)}>
            <Plus className="h-4 w-4" />
            New advertiser
          </Button>
        }
      />
      <div className="max-w-[820px] px-8 py-8">
        {open && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              create.mutate();
            }}
            className="mb-6 space-y-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]"
          >
            <Field label="Name" htmlFor="adv-name">
              <Input id="adv-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </Field>
            <Field label="Website" htmlFor="adv-web">
              <Input id="adv-web" placeholder="https://example.com" value={form.website_url} onChange={(e) => setForm({ ...form, website_url: e.target.value })} />
            </Field>
            <Field label="Industry" htmlFor="adv-ind">
              <Select id="adv-ind" value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })}>
                {INDUSTRIES.map(([v, label]) => (
                  <option key={v} value={v}>
                    {label}
                  </option>
                ))}
              </Select>
            </Field>
            {error && <p className="text-sm text-[var(--color-danger)]">{error}</p>}
            <div className="flex gap-2">
              <Button type="submit" disabled={create.isPending}>
                {create.isPending ? "Creating…" : "Create advertiser"}
              </Button>
              <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
                Cancel
              </Button>
            </div>
          </form>
        )}

        {isLoading ? (
          <p className="text-sm text-[var(--color-text-muted)]">Loading…</p>
        ) : advertisers.length === 0 ? (
          <EmptyState
            title="No advertisers yet"
            description="Add the first brand you want to advertise to start building campaigns."
            action={<Button onClick={() => setOpen(true)}>Add advertiser</Button>}
          />
        ) : (
          <div className="overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-bg-subtle)] text-left text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                <tr>
                  <th className="px-4 py-2.5 font-semibold">Name</th>
                  <th className="px-4 py-2.5 font-semibold">Industry</th>
                  <th className="px-4 py-2.5 font-semibold">Website</th>
                </tr>
              </thead>
              <tbody>
                {advertisers.map((a) => (
                  <tr key={String(a.id)} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3 font-medium text-[var(--color-text)]">{a.name}</td>
                    <td className="px-4 py-3 text-[var(--color-text-muted)]">{a.industry}</td>
                    <td className="px-4 py-3 text-[var(--color-text-muted)]">{a.website_url ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
