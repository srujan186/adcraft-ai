"use client";
import type { FormEvent } from "react";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useRef, useState } from "react";

import { EmptyState } from "@/components/app/EmptyState";
import { PageHeader } from "@/components/app/PageHeader";
import { StatusPill } from "@/components/app/StatusPill";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { type Advertiser, type AudienceT, errorMessage } from "@/lib/hooks";
import { getAccessToken, getAccountId } from "@/lib/auth";
import { API_URL, nfCompact, pct } from "@/lib/utils";

type Mode = null | "custom" | "lookalike";

export default function AudiencesPage() {
  const qc = useQueryClient();
  const [mode, setMode] = useState<Mode>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: advertisers = [] } = useQuery({
    queryKey: ["advertisers"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/advertisers");
      if (error) throw error;
      return data as Advertiser[];
    },
  });
  const { data: audiences = [] } = useQuery({
    queryKey: ["audiences"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/audiences");
      if (error) throw error;
      return data as AudienceT[];
    },
    refetchInterval: (q) =>
      (q.state.data as AudienceT[] | undefined)?.some((a) => a.status === "processing" || a.status === "counting")
        ? 1500
        : false,
  });

  const noAdv = advertisers.length === 0;
  const advId = advertisers[0] ? String(advertisers[0].id) : "";

  return (
    <>
      <PageHeader
        title="Audiences"
        subtitle="Create and save audiences to reach the people who matter to your business."
        action={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setMode(mode === "lookalike" ? null : "lookalike")} disabled={noAdv || audiences.length === 0}>
              Lookalike
            </Button>
            <Button onClick={() => setMode(mode === "custom" ? null : "custom")} disabled={noAdv}>
              <Plus className="h-4 w-4" /> New audience
            </Button>
          </div>
        }
      />
      <div className="max-w-[960px] px-8 py-8">
        {noAdv && (
          <p className="mb-4 rounded-[var(--radius-md)] bg-[var(--color-warning-50)] px-4 py-2 text-sm text-[var(--color-warning)]">
            Add an advertiser first (Settings → Advertisers).
          </p>
        )}
        {mode === "custom" && !noAdv && (
          <CustomForm advId={advId} advertisers={advertisers} onDone={() => { setMode(null); qc.invalidateQueries({ queryKey: ["audiences"] }); }} setError={setError} />
        )}
        {mode === "lookalike" && !noAdv && (
          <LookalikeForm advId={advId} advertisers={advertisers} audiences={audiences} onDone={() => { setMode(null); qc.invalidateQueries({ queryKey: ["audiences"] }); }} setError={setError} />
        )}
        {error && <p className="mb-3 text-sm text-[var(--color-danger)]">{error}</p>}

        {audiences.length === 0 ? (
          <EmptyState title="No audiences yet" description="Upload a contacts list, build a firmographic audience, or create a lookalike." />
        ) : (
          <div className="overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-bg-subtle)] text-left text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                <tr>
                  <th className="px-4 py-2.5 font-semibold">Name</th>
                  <th className="px-4 py-2.5 font-semibold">Source</th>
                  <th className="px-4 py-2.5 font-semibold">Status</th>
                  <th className="px-4 py-2.5 font-semibold">Match rate</th>
                  <th className="px-4 py-2.5 font-semibold">Matched households</th>
                </tr>
              </thead>
              <tbody>
                {audiences.map((a) => (
                  <tr key={String(a.id)} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3 font-medium text-[var(--color-text)]">{a.name}</td>
                    <td className="px-4 py-3 text-[var(--color-text-muted)]">{a.source.replace(/_/g, " ")}</td>
                    <td className="px-4 py-3"><StatusPill status={a.status} /></td>
                    <td className="px-4 py-3 tabular-nums text-[var(--color-text-muted)]">{a.match_rate != null ? pct(a.match_rate) : "—"}</td>
                    <td className="px-4 py-3 tabular-nums text-[var(--color-text-muted)]">{nfCompact.format(a.matched_households)}</td>
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

function CustomForm({ advId, advertisers, onDone, setError }: { advId: string; advertisers: Advertiser[]; onDone: () => void; setError: (s: string | null) => void }) {
  const [advertiser, setAdvertiser] = useState(advId);
  const [source, setSource] = useState("contacts_list");
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const isFile = source === "contacts_list" || source === "company_list";

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (isFile) {
        if (!file) throw { error: { message: "Choose a CSV file." } };
        const fd = new FormData();
        fd.append("advertiser_id", advertiser || advId);
        fd.append("name", name || file.name);
        fd.append("source", source);
        fd.append("file", file);
        const res = await fetch(`${API_URL}/api/v1/audiences/upload`, {
          method: "POST",
          headers: { Authorization: `Bearer ${getAccessToken() ?? ""}`, "X-Account-Id": getAccountId() ?? "" },
          body: fd,
        });
        if (!res.ok) throw await res.json();
      } else {
        const { error } = await api.POST("/api/v1/audiences", {
          body: { advertiser_id: (advertiser || advId) as never, name: name || "Firmographic audience", source: source as never, definition: {} },
        });
        if (error) throw error;
      }
      onDone();
    } catch (err) {
      setError(errorMessage(err, "Could not create audience."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="mb-6 grid gap-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)] sm:grid-cols-2">
      <Field label="Source" htmlFor="au-src">
        <Select id="au-src" value={source} onChange={(e) => setSource(e.target.value)}>
          <option value="contacts_list">Contacts list (CSV)</option>
          <option value="company_list">Company list (CSV)</option>
          <option value="firmographic">Firmographic</option>
          <option value="klaviyo">Klaviyo</option>
          <option value="hubspot">HubSpot</option>
          <option value="mailchimp">Mailchimp</option>
        </Select>
      </Field>
      <Field label="Advertiser" htmlFor="au-adv">
        <Select id="au-adv" value={advertiser} onChange={(e) => setAdvertiser(e.target.value)}>
          {advertisers.map((a) => <option key={String(a.id)} value={String(a.id)}>{a.name}</option>)}
        </Select>
      </Field>
      <Field label="Name" htmlFor="au-name">
        <Input id="au-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="My audience" />
      </Field>
      {isFile && (
        <Field label="CSV file (email, zip)" htmlFor="au-file">
          <input id="au-file" ref={fileRef} type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="block w-full text-sm" />
        </Field>
      )}
      <div className="sm:col-span-2">
        <Button type="submit" disabled={busy}>{busy ? "Creating…" : "Create audience"}</Button>
      </div>
    </form>
  );
}

function LookalikeForm({ advId, advertisers, audiences, onDone, setError }: { advId: string; advertisers: Advertiser[]; audiences: AudienceT[]; onDone: () => void; setError: (s: string | null) => void }) {
  const [advertiser, setAdvertiser] = useState(advId);
  const [seed, setSeed] = useState(audiences[0] ? String(audiences[0].id) : "");
  const [size, setSize] = useState(5);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const { error } = await api.POST("/api/v1/audiences/lookalike", {
      body: { advertiser_id: (advertiser || advId) as never, seed_audience_id: seed as never, size_pct: size, name: name || `Lookalike ${size}%` },
    });
    setBusy(false);
    if (error) return setError(errorMessage(error, "Could not create lookalike."));
    onDone();
  }

  return (
    <form onSubmit={submit} className="mb-6 grid gap-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)] sm:grid-cols-2">
      <Field label="Seed audience" htmlFor="lk-seed">
        <Select id="lk-seed" value={seed} onChange={(e) => setSeed(e.target.value)}>
          {audiences.map((a) => <option key={String(a.id)} value={String(a.id)}>{a.name}</option>)}
        </Select>
      </Field>
      <Field label="Advertiser" htmlFor="lk-adv">
        <Select id="lk-adv" value={advertiser} onChange={(e) => setAdvertiser(e.target.value)}>
          {advertisers.map((a) => <option key={String(a.id)} value={String(a.id)}>{a.name}</option>)}
        </Select>
      </Field>
      <Field label={`Size: ${size}% of US households`} htmlFor="lk-size">
        <input id="lk-size" type="range" min={1} max={10} value={size} onChange={(e) => setSize(Number(e.target.value))} className="w-full" />
      </Field>
      <Field label="Name" htmlFor="lk-name">
        <Input id="lk-name" value={name} onChange={(e) => setName(e.target.value)} placeholder={`Lookalike ${size}%`} />
      </Field>
      <div className="sm:col-span-2">
        <Button type="submit" disabled={busy || !seed}>{busy ? "Creating…" : "Create lookalike"}</Button>
      </div>
    </form>
  );
}
