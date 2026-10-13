import { expect, test } from "@playwright/test";

import { API, signedIn } from "./helpers";

const HIDDEN = [
  "/dashboard/settings/integrations-marketplace",
  "/dashboard/settings/integrations-installed",
  "/dashboard/settings/billing/invoices",
  "/dashboard/settings/billing/receipts",
  "/dashboard/settings/billing/refer",
  "/dashboard/settings/developers/applications",
];

// P0-6: clients must never land on a "… building in Mx" placeholder.
test("no settings menu entry leads to a 'building in' page", async ({ page }) => {
  await signedIn(page, "p06nav");
  await page.goto("/dashboard/settings/general");
  const links = await page.locator("aside a[href^='/dashboard/settings']").evaluateAll((as) =>
    as.map((a) => (a as HTMLAnchorElement).getAttribute("href")!),
  );
  expect(links.length).toBeGreaterThan(5);
  for (const href of HIDDEN) expect(links).not.toContain(href);
  for (const href of links) {
    await page.goto(href);
    await expect(page.getByText(/building in/i)).toHaveCount(0);
  }
});

test("unfinished settings pages are 404 when opened directly", async ({ page }) => {
  await signedIn(page, "p06url");
  for (const href of HIDDEN) {
    const res = await page.goto(href);
    expect(res?.status(), href).toBe(404);
    await expect(page.getByText(/building in/i)).toHaveCount(0);
  }
});

test("API keys: create (shown once), use, see last used, revoke", async ({ page }) => {
  await signedIn(page, "p06key");
  await page.goto("/dashboard/settings/developers/api-keys");
  await expect(page.getByText(/building in/i)).toHaveCount(0);

  await page.fill("#key-name", "Reporting script");
  await page.click("#key-create");
  const value = page.locator("#new-key-value");
  await expect(value).toContainText("lum_");
  const key = (await value.innerText()).trim();

  await page.getByRole("button", { name: "Done" }).click();
  await expect(page.locator("#new-key")).toHaveCount(0);
  await expect(page.getByText(key)).toHaveCount(0); // never shown again

  const row = page.locator("[data-key-row='Reporting script']");
  await expect(row).toContainText("Read only");
  await expect(row).toContainText("Never");

  const used = await page.request.get(`${API}/api/v1/advertisers`, { headers: { Authorization: `Bearer ${key}` } });
  expect(used.status()).toBe(200);
  await page.reload();
  await expect(row).not.toContainText("Never");

  await row.getByRole("button", { name: "Revoke" }).click();
  await row.getByRole("button", { name: "Revoke key" }).click();
  await expect(row).toContainText("Revoked");
  const after = await page.request.get(`${API}/api/v1/advertisers`, { headers: { Authorization: `Bearer ${key}` } });
  expect(after.status()).toBe(401);
});
