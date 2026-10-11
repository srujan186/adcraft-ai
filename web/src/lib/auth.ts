"use client";

/** Per-browser session: short-lived access token + active account id.
 * The refresh token lives in an httpOnly cookie the browser handles for us. */
const ACCESS = "lumen_access";
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
export function getAccountId(): string | null {
  return store()?.getItem(ACCOUNT) ?? null;
}
export function setAccountId(id: string): void {
  store()?.setItem(ACCOUNT, id);
}
export function setSession(token: string, accountId: string): void {
  setAccessToken(token);
  setAccountId(accountId);
}
export function clearSession(): void {
  const s = store();
  s?.removeItem(ACCESS);
  s?.removeItem(ACCOUNT);
}
export function isAuthed(): boolean {
  return !!getAccessToken();
}
