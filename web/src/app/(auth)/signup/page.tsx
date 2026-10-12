"use client";
import type { ChangeEvent, FormEvent } from "react";

import { Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { ACTION_TIMEOUT_MS, api, unreachableMessage, wrongServerMessage } from "@/lib/api/client";
import { setSession } from "@/lib/auth";
import { errorMessage, useSlow } from "@/lib/hooks";
import { PRODUCT_NAME } from "@/lib/utils";

export default function SignupPage() {
  const router = useRouter();
  const [form, setForm] = useState({ full_name: "", company: "", email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const slow = useSlow(busy);

  const set = (k: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (form.password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      const { data, error, response } = await api.POST("/api/v1/auth/signup", {
        body: form,
        signal: AbortSignal.timeout(ACTION_TIMEOUT_MS),
      });
      if (error || !data) {
        setError(response.status === 404 ? wrongServerMessage() : errorMessage(error, "Could not create your account."));
        return;
      }
      setSession(data.access_token, String(data.account_id), data.refresh_token);
      router.push("/dashboard");
    } catch (err) {
      // Network-level failure (CORS, server down/asleep, timeout): fetch threw, so say so.
      setError(unreachableMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center px-6">
      <div className="w-full max-w-[420px]">
        <div className="mb-6 flex items-center gap-2 text-lg font-semibold text-[var(--color-text)]">
          <span
            className="grid h-7 w-7 place-items-center rounded-[var(--radius-md)] text-white"
            style={{ background: "var(--color-primary)" }}
            aria-hidden
          >
            <Sparkles className="h-4 w-4" />
          </span>
          {PRODUCT_NAME}
        </div>
        <div className="rounded-[var(--radius-xl)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8 shadow-[var(--shadow-card)]">
          <h1 className="text-2xl font-bold text-[var(--color-text)]">Create your account</h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Launch your first streaming-TV campaign in minutes.
          </p>
          <form onSubmit={onSubmit} className="mt-6 space-y-4" id="signup-form">
            <Field label="Your name" htmlFor="full_name">
              <Input id="full_name" value={form.full_name} onChange={set("full_name")} autoComplete="name" />
            </Field>
            <Field label="Company" htmlFor="company">
              <Input id="company" value={form.company} onChange={set("company")} required />
            </Field>
            <Field label="Work email" htmlFor="email">
              <Input id="email" type="email" value={form.email} onChange={set("email")} required autoComplete="email" />
            </Field>
            <Field label="Password" htmlFor="password">
              <Input id="password" type="password" value={form.password} onChange={set("password")} required autoComplete="new-password" />
            </Field>
            {error && <p className="text-sm text-[var(--color-danger)]">{error}</p>}
            {slow && (
              <p className="text-sm text-[var(--color-text-muted)]" role="status">
                Waking the server up — the first request after a quiet period can take up to a minute.
              </p>
            )}
            <Button type="submit" className="w-full" disabled={busy} id="signup-submit">
              {busy ? "Creating…" : "Create account"}
            </Button>
          </form>
        </div>
        <p className="mt-4 text-center text-sm text-[var(--color-text-muted)]">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-[var(--color-primary)]">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
