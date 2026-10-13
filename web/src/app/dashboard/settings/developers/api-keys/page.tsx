"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { PageHeader } from "@/components/app/PageHeader";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { errorMessage } from "@/lib/hooks";
import { API_URL } from "@/lib/utils";

type ApiKey = components["schemas"]["ApiKeyOut"];
type Access = "read" | "write";

function accessLabel(scopes: string[]): string {
  if (scopes.length === 0) return "Full access (older key)";
  return scopes.includes("write") ? "Read and write" : "Read only";
}

function when(iso: string | null | undefined): string {
  return iso ? new Date(iso).toLocaleString() : "Never";
}

export default function ApiKeysPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [access, setAccess] = useState<Access>("read");
  const [created, setCreated] = useState<{ name: string; key: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const [confirming, setConfirming] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: keys = [], isLoading } = useQuery({
    queryKey: ["api-keys"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/api-keys");
      if (error) throw error;
      return (data as ApiKey[]) ?? [];
    },
  });

  const create = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/v1/api-keys", {
        body: { name: name.trim(), scopes: access === "write" ? ["read", "write"] : ["read"] },
      });
      if (error || !data) throw error;
      return data;
    },
    onSuccess: async (data) => {
      setCreated({ name: data.name, key: data.key });
      setCopied(false);
      setName("");
      setAccess("read");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
    onError: (e) => setError(errorMessage(e, "Couldn't create the key.")),
  });

  const revoke = useMutation({
    mutationFn: async (id: string) => {
      const { error } = await api.DELETE("/api/v1/api-keys/{key_id}", { params: { path: { key_id: id } } });
      if (error) throw error;
    },
    onSuccess: async () => {
      setConfirming(null);
      await qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
    onError: (e) => setError(errorMessage(e, "Couldn't revoke the key.")),
  });

  async function copy() {
    if (!created) return;
    try {
      await navigator.clipboard.writeText(created.key);
      setCopied(true);
    } catch {
      setCopied(false); // clipboard blocked: the key stays selectable on screen
    }
  }

  const sorted = [...keys].sort((a, b) => Number(!!a.revoked_at) - Number(!!b.revoked_at));

  return (
    <>
      <PageHeader title="API keys" subtitle="Let your own tools read or manage this account through the API." />
      <div className="max-w-[900px] space-y-6 px-8 py-8">
        {created && (
          <div id="new-key" role="status"
               className="rounded-[var(--radius-lg)] border border-[var(--color-success)] bg-[var(--color-success-50)] p-5">
            <h2 className="text-sm font-semibold text-[var(--color-text)]">Your new key “{created.name}”</h2>
            <p className="mt-1 text-sm text-[var(--color-text-body)]">
              Copy it now — for security it is shown only once. If you lose it, revoke it and create a new one.
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <code id="new-key-value"
                    className="min-w-0 flex-1 select-all break-all rounded-[var(--radius-md)] bg-[var(--color-surface)] px-3 py-2 font-mono text-xs text-[var(--color-text)]">
                {created.key}
              </code>
              <Button type="button" variant="outline" onClick={copy}>{copied ? "Copied" : "Copy"}</Button>
              <Button type="button" onClick={() => setCreated(null)}>Done</Button>
            </div>
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (name.trim()) create.mutate();
          }}
          className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]"
        >
          <h2 className="text-base font-semibold text-[var(--color-text)]">Create a key</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
            <Field label="Name" htmlFor="key-name">
              <Input id="key-name" value={name} placeholder="e.g. Reporting script"
                     onChange={(e) => setName(e.target.value)} required maxLength={200} />
            </Field>
            <Button type="submit" disabled={create.isPending || !name.trim()} id="key-create">
              {create.isPending ? "Creating…" : "Create key"}
            </Button>
          </div>
          <fieldset className="mt-4">
            <legend className="text-sm font-medium text-[var(--color-text)]">Access</legend>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {([
                ["read", "Read only", "View campaigns, stats and reports. Can’t change anything."],
                ["write", "Read and write", "Also create, edit, publish and delete."],
              ] as const).map(([value, label, hint]) => (
                <label key={value}
                       className={`flex cursor-pointer gap-3 rounded-[var(--radius-md)] border p-3 text-sm ${
                         access === value ? "border-[var(--color-primary)] bg-[var(--color-primary-50)]" : "border-[var(--color-border)]"}`}>
                  <input type="radio" name="key-access" id={`key-access-${value}`} value={value}
                         checked={access === value} onChange={() => setAccess(value)} className="mt-0.5" />
                  <span>
                    <span className="block font-medium text-[var(--color-text)]">{label}</span>
                    <span className="block text-xs text-[var(--color-text-muted)]">{hint}</span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
          {error && <p className="mt-3 text-sm text-[var(--color-danger)]">{error}</p>}
        </form>

        <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-[var(--color-border)]">
          <table className="w-full text-sm" id="key-table">
            <thead className="bg-[var(--color-bg-subtle)] text-left text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Name</th>
                <th className="px-4 py-2.5 font-semibold">Key</th>
                <th className="px-4 py-2.5 font-semibold">Access</th>
                <th className="px-4 py-2.5 font-semibold">Created</th>
                <th className="px-4 py-2.5 font-semibold">Last used</th>
                <th className="px-4 py-2.5 font-semibold" aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={6} className="px-4 py-4 text-[var(--color-text-muted)]">Loading…</td></tr>
              ) : sorted.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-6 text-center text-[var(--color-text-muted)]">No API keys yet.</td></tr>
              ) : (
                sorted.map((k) => {
                  const revoked = !!k.revoked_at;
                  return (
                    <tr key={String(k.id)} data-key-row={k.name}
                        className={`border-t border-[var(--color-border)] ${revoked ? "text-[var(--color-text-muted)]" : ""}`}>
                      <td className="px-4 py-3 font-medium text-[var(--color-text)]">{k.name}</td>
                      <td className="px-4 py-3 font-mono text-xs">lum_{k.prefix}…</td>
                      <td className="px-4 py-3">{accessLabel(k.scopes)}</td>
                      <td className="px-4 py-3 tabular-nums">{when(k.created_at)}</td>
                      <td className="px-4 py-3 tabular-nums">{when(k.last_used_at)}</td>
                      <td className="px-4 py-3 text-right">
                        {revoked ? (
                          <span className="rounded-full bg-[var(--color-bg-subtle)] px-2 py-0.5 text-xs font-medium">Revoked</span>
                        ) : confirming === String(k.id) ? (
                          <span className="inline-flex items-center gap-2 whitespace-nowrap">
                            <span className="text-xs text-[var(--color-text-muted)]">Tools using it will stop working.</span>
                            <Button type="button" variant="outline" onClick={() => setConfirming(null)}>Cancel</Button>
                            <Button type="button" onClick={() => revoke.mutate(String(k.id))} disabled={revoke.isPending}>
                              Revoke key
                            </Button>
                          </span>
                        ) : (
                          <Button type="button" variant="outline" onClick={() => setConfirming(String(k.id))}>Revoke</Button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div className="rounded-[var(--radius-lg)] bg-[var(--color-bg-subtle)] p-5 text-sm text-[var(--color-text-body)]">
          <h2 className="font-semibold text-[var(--color-text)]">Using a key</h2>
          <p className="mt-1">Send it as a bearer token. The key already identifies this account.</p>
          <pre className="mt-3 overflow-x-auto rounded-[var(--radius-md)] bg-[var(--color-surface)] p-3 font-mono text-xs">
{`curl -H "Authorization: Bearer lum_…" \\
  ${API_URL}/api/v1/campaigns`}
          </pre>
        </div>
      </div>
    </>
  );
}
