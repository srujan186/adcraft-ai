"use client";

import createClient, { type Middleware } from "openapi-fetch";

import { clearSession, getAccessToken, getAccountId, getRefreshToken, setAccessToken, setRefreshToken } from "@/lib/auth";
import { API_URL } from "@/lib/utils";
import type { paths } from "./schema";

export const api = createClient<paths>({ baseUrl: API_URL, credentials: "include" });

/** How long a user action waits before giving up. Free hosts cold-start in 30-90s. */
export const ACTION_TIMEOUT_MS = 90_000;

/**
 * openapi-fetch returns `{ error }` for HTTP errors but *throws* when the request never
 * completes (CORS rejection, DNS, server down or asleep, timeout). A caller that only
 * checks `error` then hangs forever with no message — so user actions catch and use this.
 */
export function unreachableMessage(err: unknown): string {
  const host = API_URL.replace(/^https?:\/\//, "");
  if (err instanceof DOMException && err.name === "TimeoutError") {
    return `The server (${host}) didn't respond in time. If it was asleep it may be awake now — please try again.`;
  }
  return `Can't reach the server (${host}). It may be down, or not set up to accept requests from this site.`;
}

/** A 404 from an auth route means NEXT_PUBLIC_API_URL points at a server without this API. */
export function wrongServerMessage(): string {
  return `The server at ${API_URL.replace(/^https?:\/\//, "")} has no login service — this site is connected to the wrong server.`;
}

// Single-flight refresh so parallel 401s don't each hit /auth/refresh.
let refreshing: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  if (!refreshing) {
    refreshing = (async () => {
      try {
        // Send the stored refresh token in the body: cross-site, the cookie never arrives.
        const r = await fetch(`${API_URL}/api/v1/auth/refresh`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: getRefreshToken() }),
        });
        if (!r.ok) return false;
        const data = (await r.json()) as { access_token: string; refresh_token?: string | null };
        setAccessToken(data.access_token);
        setRefreshToken(data.refresh_token); // rotated by the API
        return true;
      } catch {
        return false;
      }
    })();
    refreshing.finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

const auth: Middleware = {
  onRequest({ request }) {
    const token = getAccessToken();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    const account = getAccountId();
    if (account) request.headers.set("X-Account-Id", account);
    return request;
  },
  async onResponse({ request, response }) {
    // Only the credential endpoints must not trigger a refresh (that would loop or mask a
    // bad password); /auth/me is an ordinary authenticated call and should refresh.
    if (response.status !== 401 || /\/api\/v1\/auth\/(login|signup|refresh|logout)\b/.test(request.url)) {
      return response;
    }
    const ok = await tryRefresh();
    if (!ok) {
      clearSession();
      if (typeof window !== "undefined") window.location.href = "/login";
      return response;
    }
    const retry = new Request(request.url, request);
    const token = getAccessToken();
    if (token) retry.headers.set("Authorization", `Bearer ${token}`);
    const account = getAccountId();
    if (account) retry.headers.set("X-Account-Id", account);
    return fetch(retry);
  },
};

api.use(auth);

export type { paths };


/**
 * Query retry policy. A sleeping free-tier server answers with a gateway error page (non-JSON),
 * a 5xx, or no response at all while it wakes — retry those with backoff (1s, 2s, 4s, 8s).
 * Our own JSON errors (401, 403, 404, 422…) are answers, not outages: never retry them.
 */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (failureCount >= 4) return false;
  if (error instanceof TypeError || error instanceof DOMException) return true; // network / timeout
  if (typeof error === "string") return true; // HTML gateway page, not our API
  const code = (error as { error?: { code?: string } } | null)?.error?.code;
  return !code || code === "INTERNAL_ERROR";
}

export const retryDelay = (attempt: number) => Math.min(1000 * 2 ** attempt, 8000);
