"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { clearSession } from "@/lib/auth";

export type Me = components["schemas"]["MeResponse"];
export type Advertiser = components["schemas"]["AdvertiserOut"];
export type Member = components["schemas"]["MemberOut"];
export type Creative = components["schemas"]["CreativeOut"];
export type Campaign = components["schemas"]["CampaignOut"];
export type CampaignDetail = components["schemas"]["CampaignDetail"];
export type Strategy = components["schemas"]["StrategyOut"];
export type Estimate = components["schemas"]["EstimateResponse"];
export type AudienceT = components["schemas"]["AudienceOut"];

/** Shape of our API error envelope. */
export function errorMessage(err: unknown, fallback = "Something went wrong"): string {
  // Our API's envelope is {error:{message}}; FastAPI defaults (and other servers) use {detail}.
  const e = err as { error?: { message?: string }; detail?: unknown } | undefined;
  if (e?.error?.message) return e.error.message;
  if (typeof e?.detail === "string") return e.detail;
  return fallback;
}

/** True once `busy` has lasted `ms` — for "the server is waking up" hints on free hosts. */
export function useSlow(busy: boolean, ms = 6000): boolean {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    if (!busy) {
      setSlow(false);
      return;
    }
    const t = setTimeout(() => setSlow(true), ms);
    return () => clearTimeout(t);
  }, [busy, ms]);
  return slow;
}

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/auth/me");
      if (error) throw error;
      return data as Me;
    },
    // Loaded once and shared by every component (React Query dedupes); the user and account
    // rarely change mid-session. Retries follow the app-wide policy (server waking up).
    staleTime: 5 * 60_000,
  });
}

export async function logout(): Promise<void> {
  try {
    await api.POST("/api/v1/auth/logout");
  } catch {
    /* ignore */
  }
  clearSession();
  if (typeof window !== "undefined") window.location.href = "/login";
}
