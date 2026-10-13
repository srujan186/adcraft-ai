import { expect, test } from "@playwright/test";

import { API, signedIn } from "./helpers";

// P0-7: Studio must refuse to make an ad from a website the advertiser doesn't own.
test("advertiser without a website can add one, and Studio prefills it", async ({ page }) => {
  const s = await signedIn(page, "p07a");
  await page.request.post(`${API}/api/v1/advertisers`, {
    headers: s.headers,
    data: { name: "Nimbus Goods", industry: "ecommerce", timezone: "America/New_York" },
  });

  await page.goto("/dashboard/settings/advertisers");
  await page.getByRole("button", { name: "Add website" }).click();
  await page.getByLabel("Website for Nimbus Goods").fill("https://www.nimbusgoods.example");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("https://www.nimbusgoods.example")).toBeVisible();

  await page.goto("/dashboard/library/studio");
  await page.locator("#s-adv").selectOption({ label: "Nimbus Goods" });
  await expect(page.locator("#s-url")).toHaveValue("https://www.nimbusgoods.example");
  await expect(page.getByText(/only be made from Nimbus Goods's own website/)).toBeVisible();
});

test("Studio refuses someone else's website with a clear message", async ({ page }) => {
  const s = await signedIn(page, "p07b");
  await page.request.post(`${API}/api/v1/advertisers`, {
    headers: s.headers,
    data: { name: "Nimbus Goods", industry: "ecommerce", timezone: "America/New_York",
            website_url: "https://nimbusgoods.example" },
  });
  await page.goto("/dashboard/library/studio");
  await page.locator("#s-url").fill("https://otherbrand.example");
  await page.getByRole("button", { name: /Generate creative/ }).click();
  await expect(page.getByText(/own website \(nimbusgoods\.example\); otherbrand\.example doesn't match/)).toBeVisible();
});
