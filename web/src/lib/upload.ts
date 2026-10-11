"use client";

import { getAccessToken, getAccountId } from "@/lib/auth";
import { API_URL } from "@/lib/utils";

/** Multipart creative upload (goes through the API to avoid browser→storage CORS). */
export async function uploadCreative(advertiserId: string, name: string, file: File) {
  const fd = new FormData();
  fd.append("advertiser_id", advertiserId);
  fd.append("name", name);
  fd.append("file", file);
  const res = await fetch(`${API_URL}/api/v1/creatives/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${getAccessToken() ?? ""}`,
      "X-Account-Id": getAccountId() ?? "",
    },
    body: fd,
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: "Upload failed" } }));
    throw err;
  }
  return res.json();
}
