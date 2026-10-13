import type { Page } from "@playwright/test";

export const API = process.env.E2E_API_URL ?? "http://127.0.0.1:8000";

export type Session = { token: string; accountId: string; headers: Record<string, string> };

/** Sign up a fresh user through the API and put the session into the browser. */
export async function signedIn(page: Page, label = "e2e"): Promise<Session> {
  const email = `${label}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@acme.io`;
  const r = await page.request.post(`${API}/api/v1/auth/signup`, {
    data: { email, password: "password123", full_name: "E2E User", company: "E2E Co" },
  });
  if (!r.ok()) throw new Error(`signup failed: ${r.status()} ${await r.text()}`);
  const d = await r.json();
  const s: Session = {
    token: d.access_token,
    accountId: String(d.account_id),
    headers: { Authorization: `Bearer ${d.access_token}`, "X-Account-Id": String(d.account_id) },
  };
  await page.goto("/login");
  await page.evaluate(
    ([t, a, rt]) => {
      localStorage.setItem("lumen_access", t);
      localStorage.setItem("lumen_account_id", a);
      if (rt) localStorage.setItem("lumen_refresh", rt);
    },
    [s.token, s.accountId, d.refresh_token ?? ""],
  );
  return s;
}

export async function createAdvertiser(page: Page, s: Session, name = "Nimbus Goods"): Promise<string> {
  const r = await page.request.post(`${API}/api/v1/advertisers`, {
    headers: s.headers,
    data: { name, industry: "ecommerce", timezone: "America/New_York", website: "https://nimbusgoods.example" },
  });
  if (!r.ok()) throw new Error(`advertiser failed: ${r.status()} ${await r.text()}`);
  return (await r.json()).id;
}

/** Log in as a fixed account, creating it the first time (for allow-listed admin emails). */
export async function signedInAs(page: Page, email: string, password = "password123"): Promise<Session> {
  let r = await page.request.post(`${API}/api/v1/auth/login`, { data: { email, password } });
  if (r.status() === 401) {
    r = await page.request.post(`${API}/api/v1/auth/signup`, {
      data: { email, password, full_name: "E2E Admin", company: "E2E Co" },
    });
  }
  if (!r.ok()) throw new Error(`login failed: ${r.status()} ${await r.text()}`);
  const d = await r.json();
  const s: Session = {
    token: d.access_token,
    accountId: String(d.account_id),
    headers: { Authorization: `Bearer ${d.access_token}`, "X-Account-Id": String(d.account_id) },
  };
  await page.goto("/login");
  await page.evaluate(
    ([t, a, rt]) => {
      localStorage.setItem("lumen_access", t);
      localStorage.setItem("lumen_account_id", a);
      if (rt) localStorage.setItem("lumen_refresh", rt);
    },
    [s.token, s.accountId, d.refresh_token ?? ""],
  );
  return s;
}
