"use client";

import createClient, { type Middleware } from "openapi-fetch";

import { clearSession, getAccessToken, getAccountId, setAccessToken } from "@/lib/auth";
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
        const r = await fetch(`${API_URL}/api/v1/auth/refresh`, {
          method: "POST",
          credentials: "include",
        });
        if (!r.ok) return false;
        const data = (await r.json()) as { access_token: string };
        setAccessToken(data.access_token);
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
    if (response.status !== 401 || request.url.includes("/api/v1/auth/")) return response;
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
