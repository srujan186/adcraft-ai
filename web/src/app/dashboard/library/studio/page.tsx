"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PageHeader } from "@/components/app/PageHeader";
import { StatusPill } from "@/components/app/StatusPill";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { type Advertiser, errorMessage } from "@/lib/hooks";

interface Job {
  id: string; status: string; error: string | null;
  creative: { id: string; name: string; review_status: string; width: number; height: number; duration_ms: number; video_url: string | null; thumbnail_url: string | null } | null;
}

export default function StudioPage() {
  const [form, setForm] = useState({ advertiser_id: "", url: "", business_name: "", duration_s: 15, tone: "informative", cta: "Learn more" });
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: advertisers = [] } = useQuery({
    queryKey: ["advertisers"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/advertisers");
      if (error) throw error;
      return data as Advertiser[];
    },
  });

  const { data: job } = useQuery({
    queryKey: ["studio-job", jobId],
    enabled: !!jobId,
    refetchInterval: (q) => ((q.state.data as Job | undefined)?.status === "done" || (q.state.data as Job | undefined)?.status === "error" ? false : 1500),
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/studio/jobs/{job_id}", { params: { path: { job_id: jobId! } } });
      return data as Job;
    },
  });

  const generate = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/v1/studio/jobs", {
        body: {
          advertiser_id: (form.advertiser_id || advertisers[0]?.id || "") as string,
          url: form.url || null, business_name: form.business_name || null,
          duration_s: form.duration_s, tone: form.tone, cta: form.cta,
        } as never,
      });
      if (error) throw error;
      return data as { id: string };
    },
    onSuccess: (d) => { setJobId(d.id); setError(null); },
    onError: (e) => setError(errorMessage(e, "Could not start generation.")),
  });

  const noAdv = advertisers.length === 0;
  const working = job && (job.status === "pending" || job.status === "processing");

  return (
    <>
      <PageHeader title="Studio" subtitle="Turn a business URL into a narrated streaming-TV creative." />
      <div className="grid max-w-[1000px] grid-cols-12 gap-6 px-8 py-8">
        <div className="col-span-12 space-y-4 lg:col-span-5">
          {noAdv && <p className="rounded-[var(--radius-md)] bg-[var(--color-warning-50)] px-4 py-2 text-sm text-[var(--color-warning)]">Add an advertiser first.</p>}
          <div className="space-y-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]">
            <Field label="Advertiser" htmlFor="s-adv">
              <Select id="s-adv" value={form.advertiser_id} onChange={(e) => setForm({ ...form, advertiser_id: e.target.value })}>
                {advertisers.map((a) => <option key={String(a.id)} value={String(a.id)}>{a.name}</option>)}
              </Select>
            </Field>
            <Field label="Business URL" htmlFor="s-url">
              <Input id="s-url" placeholder="https://your-site.com (or leave blank)" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Length" htmlFor="s-dur">
                <Select id="s-dur" value={form.duration_s} onChange={(e) => setForm({ ...form, duration_s: Number(e.target.value) })}>
                  <option value={15}>15 seconds</option>
                  <option value={30}>30 seconds</option>
                </Select>
              </Field>
              <Field label="Tone" htmlFor="s-tone">
                <Select id="s-tone" value={form.tone} onChange={(e) => setForm({ ...form, tone: e.target.value })}>
                  {["energetic", "premium", "friendly", "informative"].map((t) => <option key={t} value={t}>{t}</option>)}
                </Select>
              </Field>
            </div>
            <Field label="Call to action" htmlFor="s-cta">
              <Input id="s-cta" value={form.cta} onChange={(e) => setForm({ ...form, cta: e.target.value })} />
            </Field>
            {error && <p className="text-sm text-[var(--color-danger)]">{error}</p>}
            <Button onClick={() => generate.mutate()} disabled={noAdv || generate.isPending || !!working}>
              <Sparkles className="h-4 w-4" />
              {working ? "Generating…" : "Generate creative"}
            </Button>
          </div>
        </div>

        <div className="col-span-12 lg:col-span-7">
          <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]">
            {!job ? (
              <div className="grid h-64 place-items-center text-sm text-[var(--color-text-muted)]">Your generated ad will appear here.</div>
            ) : working ? (
              <div className="grid h-64 place-items-center text-sm text-[var(--color-text-muted)]">Generating your ad… (scrape → script → render)</div>
            ) : job.status === "error" ? (
              <p className="text-sm text-[var(--color-danger)]">Generation failed: {job.error}</p>
            ) : job.creative ? (
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="font-medium text-[var(--color-text)]">{job.creative.name}</h3>
                  <StatusPill status={job.creative.review_status} />
                </div>
                {job.creative.video_url && (
                  // eslint-disable-next-line jsx-a11y/media-has-caption
                  <video src={job.creative.video_url} controls className="w-full rounded-[var(--radius-lg)] bg-black" />
                )}
                <p className="mt-3 text-sm text-[var(--color-text-muted)]">
                  {job.creative.width}×{job.creative.height} · {Math.round((job.creative.duration_ms ?? 0) / 1000)}s · saved to your Library.
                </p>
                <div className="mt-3 flex gap-2">
                  <Button variant="outline" onClick={() => generate.mutate()}>Regenerate</Button>
                  <Button asChild><Link href="/dashboard/library">Go to Library</Link></Button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </>
  );
}
