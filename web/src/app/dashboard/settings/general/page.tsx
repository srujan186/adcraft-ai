"use client";
import type { ChangeEvent, FormEvent } from "react";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/app/PageHeader";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { errorMessage, useMe } from "@/lib/hooks";

const TIMEZONES = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Phoenix",
  "UTC",
];

export default function GeneralSettingsPage() {
  const qc = useQueryClient();
  const { data: me, isLoading } = useMe();
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState("America/New_York");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (me?.active_account) {
      setName(me.active_account.name);
      setTimezone(me.active_account.timezone);
    }
  }, [me]);

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!me) return;
    setBusy(true);
    setMsg(null);
    const { error } = await api.PATCH("/api/v1/accounts/{account_id}", {
      params: { path: { account_id: String(me.active_account.id) } },
      body: { name, timezone },
    });
    setBusy(false);
    if (error) {
      setMsg({ ok: false, text: errorMessage(error, "Could not save changes.") });
      return;
    }
    await qc.invalidateQueries({ queryKey: ["me"] });
    setMsg({ ok: true, text: "Saved." });
  }

  return (
    <>
      <PageHeader title="General" subtitle="Account name, timezone and currency." />
      <div className="max-w-[640px] px-8 py-8">
        <form onSubmit={save} className="space-y-5 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]">
          <Field label="Account name" htmlFor="acct-name">
            <Input id="acct-name" value={name} onChange={(e) => setName(e.target.value)} disabled={isLoading} />
          </Field>
          <Field label="Timezone" htmlFor="acct-tz">
            <Select id="acct-tz" value={timezone} onChange={(e) => setTimezone(e.target.value)} disabled={isLoading}>
              {TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Currency" htmlFor="acct-cur">
            <Input id="acct-cur" value={me?.active_account.currency ?? "USD"} disabled />
          </Field>
          <div className="flex items-center gap-3">
            <Button type="submit" disabled={busy || isLoading}>
              {busy ? "Saving…" : "Save changes"}
            </Button>
            {msg && (
              <span className={msg.ok ? "text-sm text-[var(--color-success)]" : "text-sm text-[var(--color-danger)]"}>
                {msg.text}
              </span>
            )}
          </div>
        </form>
      </div>
    </>
  );
}
