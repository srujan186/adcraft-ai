"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Sparkles, Upload, X } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";

import { CreativeThumb, CreativeVideo } from "@/components/app/CreativeMedia";
import { EmptyState } from "@/components/app/EmptyState";
import { PageHeader } from "@/components/app/PageHeader";
import { StatusPill } from "@/components/app/StatusPill";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { type Advertiser, type Creative, errorMessage } from "@/lib/hooks";
import { uploadCreative } from "@/lib/upload";

function duration(ms: number | null): string {
  if (!ms) return "—";
  const s = Math.round(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export default function LibraryPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [advertiserId, setAdvertiserId] = useState("");
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<Creative | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: advertisers = [] } = useQuery({
    queryKey: ["advertisers"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/advertisers");
      if (error) throw error;
      return data as Advertiser[];
    },
  });

  const { data: creatives = [] } = useQuery({
    queryKey: ["creatives"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/creatives");
      if (error) throw error;
      return data as Creative[];
    },
    refetchInterval: (q) =>
      (q.state.data as Creative[] | undefined)?.some(
        (c) => c.review_status === "pending" || c.review_status === "processing",
      )
        ? 2000
        : false,
  });

  const upload = useMutation({
    mutationFn: async () => {
      if (!file) throw { error: { message: "Choose a video file." } };
      return uploadCreative(advertiserId || advertisers[0]?.id || "", name || file.name, file);
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["creatives"] });
      setOpen(false);
      setName("");
      setFile(null);
      setError(null);
      if (fileRef.current) fileRef.current.value = "";
    },
    onError: (e) => setError(errorMessage(e, "Upload failed.")),
  });

  const noAdvertiser = advertisers.length === 0;

  return (
    <>
      <PageHeader
        title="Library"
        subtitle="Import and manage your creatives."
        action={
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <Link href="/dashboard/library/studio">
                <Sparkles className="h-4 w-4" />
                Create with AI
              </Link>
            </Button>
            <Button onClick={() => setOpen((v) => !v)} disabled={noAdvertiser}>
              <Upload className="h-4 w-4" />
              Upload
            </Button>
          </div>
        }
      />
      <div className="max-w-[1000px] px-8 py-8">
        {noAdvertiser && (
          <p className="mb-4 rounded-[var(--radius-md)] bg-[var(--color-warning-50)] px-4 py-2 text-sm text-[var(--color-warning)]">
            Add an advertiser first (Settings → Advertisers) before uploading creatives.
          </p>
        )}

        {open && !noAdvertiser && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              upload.mutate();
            }}
            className="mb-6 space-y-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]"
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Advertiser" htmlFor="up-adv">
                <Select id="up-adv" value={advertiserId} onChange={(e) => setAdvertiserId(e.target.value)}>
                  {advertisers.map((a) => (
                    <option key={String(a.id)} value={String(a.id)}>
                      {a.name}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Creative name" htmlFor="up-name">
                <Input id="up-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Hero 15s" />
              </Field>
            </div>
            <Field label="Video file (.mp4, 5–90s, 16:9 1080p recommended)" htmlFor="up-file">
              <input
                id="up-file"
                ref={fileRef}
                type="file"
                accept="video/mp4,video/*"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="block w-full text-sm text-[var(--color-text-body)] file:mr-3 file:rounded-[var(--radius-md)] file:border-0 file:bg-[var(--color-primary-50)] file:px-3 file:py-2 file:text-sm file:font-medium file:text-[var(--color-primary)]"
              />
            </Field>
            {error && <p className="text-sm text-[var(--color-danger)]">{error}</p>}
            <div className="flex gap-2">
              <Button type="submit" disabled={upload.isPending || !file}>
                {upload.isPending ? "Uploading…" : "Upload & process"}
              </Button>
              <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
                Cancel
              </Button>
            </div>
          </form>
        )}

        {creatives.length === 0 ? (
          <EmptyState
            title="No creatives yet"
            description="Upload a 15s or 30s video ad. We automatically review it and transcode to 1080p."
          />
        ) : (
          <div className="overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-bg-subtle)] text-left text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                <tr>
                  <th className="px-4 py-2.5 font-semibold">Preview</th>
                  <th className="px-4 py-2.5 font-semibold">Name</th>
                  <th className="px-4 py-2.5 font-semibold">Review</th>
                  <th className="px-4 py-2.5 font-semibold">Duration</th>
                  <th className="px-4 py-2.5 font-semibold">Added</th>
                </tr>
              </thead>
              <tbody>
                {creatives.map((c) => (
                  <tr key={String(c.id)} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3">
                      <button
                        onClick={() => c.video_url && setPreview(c)}
                        className="relative grid h-12 w-20 place-items-center overflow-hidden rounded-[var(--radius-sm)] bg-slate-100"
                      >
                        <CreativeThumb src={c.thumbnail_url} alt={c.name} className="h-full w-full object-cover" />
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-[var(--color-text)]">{c.name}</div>
                      {c.review_notes && c.review_status === "rejected" && (
                        <div className="text-xs text-[var(--color-danger)]">{c.review_notes}</div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <StatusPill status={c.review_status} />
                    </td>
                    <td className="px-4 py-3 tabular-nums text-[var(--color-text-muted)]">{duration(c.duration_ms)}</td>
                    <td className="px-4 py-3 text-[var(--color-text-muted)]">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Dialog.Root open={!!preview} onOpenChange={(o) => !o && setPreview(null)}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(900px,92vw)] -translate-x-1/2 -translate-y-1/2 rounded-[var(--radius-xl)] bg-black p-2 shadow-[var(--shadow-pop)]">
            <Dialog.Title className="sr-only">{preview?.name}</Dialog.Title>
            <Dialog.Close className="absolute right-3 top-3 z-10 grid h-8 w-8 place-items-center rounded-full bg-black/60 text-white">
              <X className="h-4 w-4" />
            </Dialog.Close>
            {preview?.video_url && (
              <CreativeVideo key={preview.id} src={preview.video_url} className="w-full rounded-[var(--radius-lg)]" />
            )}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}
