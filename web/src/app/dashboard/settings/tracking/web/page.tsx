"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, ExternalLink } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PageHeader } from "@/components/app/PageHeader";
import { StatusPill } from "@/components/app/StatusPill";
import { Button } from "@/components/ui/button";
import { Field, Select } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { type Advertiser, errorMessage } from "@/lib/hooks";
import { API_URL } from "@/lib/utils";

const METHODS = ["manual", "shopify", "gtm", "s2s", "wordpress", "woocommerce", "wix", "squarespace", "bigcommerce"];

function snippet(key: string): string {
  return (
    `<script>!function(w,d,k){w.lumen=w.lumen||function(){(w.lumen.q=w.lumen.q||[]).push(arguments)};` +
    `var s=d.createElement('script');s.async=1;s.src='${API_URL}/px.js';d.head.appendChild(s);` +
    `w.lumen('init',k);w.lumen('track','page_view');}(window,document,'${key}');</script>`
  );
}

interface Pixel {
  id: string;
  advertiser_id: string;
  public_key: string;
  status: string;
  last_event_at: string | null;
}

export default function WebPixelPage() {
  const qc = useQueryClient();
  const [advertiserId, setAdvertiserId] = useState("");
  const [method, setMethod] = useState("manual");
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const { data: advertisers = [] } = useQuery({
    queryKey: ["advertisers"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/advertisers");
      if (error) throw error;
      return data as Advertiser[];
    },
  });
  const activeAdv = advertiserId || (advertisers[0] ? String(advertisers[0].id) : "");

  const { data: pixels = [] } = useQuery({
    queryKey: ["pixels"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/pixels");
      if (error) throw error;
      return data as Pixel[];
    },
  });
  const pixel = pixels.find((p) => p.advertiser_id === activeAdv);

  const setup = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/v1/advertisers/{advertiser_id}/pixel", {
        params: { path: { advertiser_id: activeAdv } },
        body: { install_method: method as never },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["pixels"] });
      setError(null);
    },
    onError: (e) => setError(errorMessage(e, "Could not set up pixel.")),
  });

  const { data: status } = useQuery({
    queryKey: ["pixel-status", pixel?.id],
    enabled: !!pixel,
    refetchInterval: 2500,
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/pixels/{pixel_id}/status", {
        params: { path: { pixel_id: String(pixel!.id) } },
      });
      return data as { status: string; events: { event: string; seen: boolean; count_24h: number }[] };
    },
  });

  const sendTest = async () => {
    if (!pixel) return;
    await api.POST("/api/v1/pixels/{pixel_id}/test-event", { params: { path: { pixel_id: String(pixel.id) } } });
    qc.invalidateQueries({ queryKey: ["pixel-status", pixel.id] });
  };

  if (advertisers.length === 0) {
    return (
      <>
        <PageHeader title="Web Pixel" subtitle="Install the pixel to measure visits and sales." />
        <div className="px-8 py-8">
          <p className="rounded-[var(--radius-md)] bg-[var(--color-warning-50)] px-4 py-2 text-sm text-[var(--color-warning)]">
            Add an advertiser first (Settings → Advertisers).
          </p>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader title="Web Pixel" subtitle="Install the pixel to measure visits and sales." />
      <div className="max-w-[760px] space-y-6 px-8 py-8">
        <Field label="Advertiser" htmlFor="px-adv">
          <Select id="px-adv" value={activeAdv} onChange={(e) => setAdvertiserId(e.target.value)}>
            {advertisers.map((a) => (
              <option key={String(a.id)} value={String(a.id)}>
                {a.name}
              </option>
            ))}
          </Select>
        </Field>

        {!pixel ? (
          <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]">
            <h2 className="text-base font-semibold text-[var(--color-text)]">Set up a pixel</h2>
            <p className="mt-1 text-sm text-[var(--color-text-muted)]">
              No web tracker set up for this advertiser yet.
            </p>
            <div className="mt-4 max-w-xs">
              <Field label="Install method" htmlFor="px-method">
                <Select id="px-method" value={method} onChange={(e) => setMethod(e.target.value)}>
                  {METHODS.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            {error && <p className="mt-2 text-sm text-[var(--color-danger)]">{error}</p>}
            <Button className="mt-4" onClick={() => setup.mutate()} disabled={setup.isPending}>
              {setup.isPending ? "Setting up…" : "Set up pixel"}
            </Button>
          </div>
        ) : (
          <>
            <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold text-[var(--color-text)]">Install snippet</h2>
                <StatusPill status={pixel.status === "active" ? "delivering" : "draft"} />
              </div>
              <p className="mt-1 text-sm text-[var(--color-text-muted)]">
                Paste this before <code>&lt;/head&gt;</code> on every page of your site.
              </p>
              <pre className="mt-3 overflow-x-auto rounded-[var(--radius-md)] bg-[var(--color-bg-subtle)] p-3 text-xs text-[var(--color-text-body)]">
                {snippet(pixel.public_key)}
              </pre>
              <Button
                variant="outline"
                className="mt-3"
                onClick={() => {
                  navigator.clipboard?.writeText(snippet(pixel.public_key));
                  setCopied(true);
                  setTimeout(() => setCopied(false), 1500);
                }}
              >
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {copied ? "Copied" : "Copy snippet"}
              </Button>
            </div>

            <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]">
              <h2 className="text-base font-semibold text-[var(--color-text)]">Verify</h2>
              <p className="mt-1 text-sm text-[var(--color-text-muted)]">
                Waiting for events… visit your site (or the demo store) to see them turn green.
              </p>
              <ul className="mt-4 space-y-2">
                {(status?.events ?? []).map((e) => (
                  <li key={e.event} className="flex items-center gap-2 text-sm">
                    <span
                      className={`grid h-5 w-5 place-items-center rounded-full ${e.seen ? "bg-[var(--color-success)] text-white" : "bg-slate-200 text-slate-400"}`}
                    >
                      {e.seen && <Check className="h-3 w-3" />}
                    </span>
                    <span className="capitalize text-[var(--color-text-body)]">{e.event.replace("_", " ")}</span>
                    {e.count_24h > 0 && <span className="text-xs text-[var(--color-text-muted)]">({e.count_24h} in 24h)</span>}
                  </li>
                ))}
              </ul>
              <div className="mt-4 flex gap-2">
                <Button variant="outline" onClick={sendTest}>
                  Send test event
                </Button>
                <Button variant="ghost" asChild>
                  <Link href="/demo-store" target="_blank">
                    Open demo store <ExternalLink className="h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
