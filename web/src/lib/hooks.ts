"use client";

import { useQuery } from "@tanstack/react-query";

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
  const e = err as { error?: { message?: string } } | undefined;
  return e?.error?.message ?? fallback;
}

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/auth/me");
      if (error) throw error;
      return data as Me;
    },
    retry: false,
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
