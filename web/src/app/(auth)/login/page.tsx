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

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const slow = useSlow(busy);

  const set = (k: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const { data, error, response } = await api.POST("/api/v1/auth/login", {
        body: form,
        signal: AbortSignal.timeout(ACTION_TIMEOUT_MS),
      });
      if (error || !data) {
        setError(response.status === 404 ? wrongServerMessage() : errorMessage(error, "Invalid email or password."));
        return;
      }
      setSession(data.access_token, String(data.account_id));
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
          <h1 className="text-2xl font-bold text-[var(--color-text)]">Log in</h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">Welcome back to {PRODUCT_NAME}.</p>
          <form onSubmit={onSubmit} className="mt-6 space-y-4" id="login-form">
            <Field label="Email" htmlFor="email">
              <Input id="email" type="email" value={form.email} onChange={set("email")} required autoComplete="email" />
            </Field>
            <Field label="Password" htmlFor="password">
              <Input id="password" type="password" value={form.password} onChange={set("password")} required autoComplete="current-password" />
            </Field>
            {error && <p className="text-sm text-[var(--color-danger)]">{error}</p>}
            {slow && (
              <p className="text-sm text-[var(--color-text-muted)]" role="status">
                Waking the server up — the first request after a quiet period can take up to a minute.
              </p>
            )}
            <Button type="submit" className="w-full" disabled={busy} id="login-submit">
              {busy ? "Logging in…" : "Log in"}
            </Button>
          </form>
        </div>
        <p className="mt-4 text-center text-sm text-[var(--color-text-muted)]">
          New to {PRODUCT_NAME}?{" "}
          <Link href="/signup" className="font-medium text-[var(--color-primary)]">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
