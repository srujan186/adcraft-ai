"use client";

/** Per-browser session: short-lived access token, refresh token, active account id.
 * The API also sets the refresh token as an httpOnly cookie, but when the web app and
 * API are on different sites (Vercel + Render/HF) browsers won't store or send that
 * cookie — so we keep the copy the API returns and post it to /auth/refresh ourselves. */
const ACCESS = "lumen_access";
const REFRESH = "lumen_refresh";
const ACCOUNT = "lumen_account_id";

function store(): Storage | null {
  try {
    return typeof window !== "undefined" ? window.localStorage : null;
  } catch {
    return null;
  }
}

export function getAccessToken(): string | null {
  return store()?.getItem(ACCESS) ?? null;
}
export function setAccessToken(token: string): void {
  store()?.setItem(ACCESS, token);
}
export function getRefreshToken(): string | null {
  return store()?.getItem(REFRESH) ?? null;
}
export function setRefreshToken(token: string | null | undefined): void {
  if (token) store()?.setItem(REFRESH, token);
}
export function getAccountId(): string | null {
  return store()?.getItem(ACCOUNT) ?? null;
}
export function setAccountId(id: string): void {
  store()?.setItem(ACCOUNT, id);
}
export function setSession(token: string, accountId: string, refreshToken?: string | null): void {
  setAccessToken(token);
  setAccountId(accountId);
  setRefreshToken(refreshToken);
}
export function clearSession(): void {
  const s = store();
  s?.removeItem(ACCESS);
  s?.removeItem(REFRESH);
  s?.removeItem(ACCOUNT);
}
export function isAuthed(): boolean {
  return !!getAccessToken();
}
