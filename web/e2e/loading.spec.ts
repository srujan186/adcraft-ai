import { expect, test } from "@playwright/test";

import { API, createAdvertiser, signedIn } from "./helpers";

const CORS = { "access-control-allow-origin": "http://localhost:3000", "access-control-allow-credentials": "true" };

// P0-5: while the account loads (a sleeping server takes 10–20 s) the header showed "Your account".
test("a slow account load shows a skeleton, never a placeholder name", async ({ page }) => {
  await signedIn(page, "p05slow");
  await page.route("**/api/v1/auth/me", async (route) => {
    await new Promise((r) => setTimeout(r, 3000));
    await route.continue();
  });
  await page.goto("/dashboard/campaigns");
  await expect(page.locator("[data-skeleton='account']")).toBeVisible();
  await expect(page.getByText("Your account")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /E2E Co/ })).toBeVisible({ timeout: 15_000 });
});

test("the account loads after the server answers 503 while waking up", async ({ page }) => {
  await signedIn(page, "p05wake");
  let calls = 0;
  await page.route("**/api/v1/auth/me", async (route) => {
    calls += 1;
    if (calls <= 2) {
      await route.fulfill({ status: 503, headers: { ...CORS, "content-type": "text/html" }, body: "<h1>Service waking up</h1>" });
    } else {
      await route.continue();
    }
  });
  await page.goto("/dashboard/campaigns");
  await expect(page.getByRole("button", { name: /E2E Co/ })).toBeVisible({ timeout: 20_000 });
  expect(calls).toBeGreaterThanOrEqual(3);
});

test("a warm reload of Campaigns shows real data in under 3 s and stays logged in", async ({ page }) => {
  const s = await signedIn(page, "p05warm");
  const adv = await createAdvertiser(page, s);
  await page.request.post(`${API}/api/v1/campaigns`, {
    headers: s.headers,
    data: { advertiser_id: adv, name: "Reload check", goal: "traffic", kpi: "cps" },
  });
  await page.goto("/dashboard/campaigns");
  await expect(page.getByText("Reload check")).toBeVisible();

  const t0 = Date.now();
  await page.reload();
  await expect(page.getByText("Reload check")).toBeVisible();
  expect(Date.now() - t0).toBeLessThan(3000);
  expect(new URL(page.url()).pathname).toBe("/dashboard/campaigns");
});
