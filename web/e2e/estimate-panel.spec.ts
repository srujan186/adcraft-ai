import { expect, type Page, test } from "@playwright/test";

import { API, createAdvertiser, signedIn } from "./helpers";

const CORS = {
  "access-control-allow-origin": "http://localhost:3000",
  "access-control-allow-credentials": "true",
};

async function draftCampaign(page: Page): Promise<string> {
  const s = await signedIn(page, "p03");
  const adv = await createAdvertiser(page, s);
  const r = await page.request.post(`${API}/api/v1/campaigns`, {
    headers: s.headers,
    data: { advertiser_id: adv, name: "Estimate check", goal: "traffic", kpi: "cps" },
  });
  return (await r.json()).id;
}

// P0-3: a failed estimate kept showing the previous numbers with no sign anything was wrong.
test("a failed estimate update says so and recovers with Try again", async ({ page }) => {
  const id = await draftCampaign(page);
  await page.route("**/api/v1/estimate", (route) =>
    route.fulfill({
      status: 500,
      headers: CORS,
      json: { error: { code: "INTERNAL_ERROR", message: "Something went wrong on our side. Please try again." } },
    }),
  );
  await page.goto(`/dashboard/campaigns/${id}/edit`);
  await expect(page.locator("#estimate-error")).toContainText("Couldn't update estimate");

  await page.unroute("**/api/v1/estimate");
  await page.locator("#estimate-error").getByRole("button", { name: "Try again" }).click();
  await expect(page.locator("#estimate-error")).toHaveCount(0);
  await expect(page.getByText("Audience size")).toBeVisible();
});

test("a network failure on estimate is shown, not swallowed", async ({ page }) => {
  const id = await draftCampaign(page);
  await page.route("**/api/v1/estimate", (route) => route.abort("connectionrefused"));
  await page.goto(`/dashboard/campaigns/${id}/edit`);
  await expect(page.locator("#estimate-error")).toContainText("Couldn't update estimate");
});
