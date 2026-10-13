import { expect, test } from "@playwright/test";

import { createAdvertiser, signedIn } from "./helpers";

// P0-8: typing a name produced "Untitled campaignSpring Sale" — the default was a value, not a placeholder.
test("the typed campaign name replaces the default instead of being appended", async ({ page }) => {
  const s = await signedIn(page, "p08");
  await createAdvertiser(page, s);

  await page.goto("/dashboard/campaigns/new");
  const name = page.locator("#c-name");
  await name.click();
  await page.keyboard.type("Spring Sale"); // what a person does: click in and type
  await page.getByRole("button", { name: "Continue to strategy" }).click();

  await page.waitForURL(/\/dashboard\/campaigns\/[^/]+\/edit/);
  await expect(page.getByText(/You are creating/)).toContainText("Spring Sale");
  await expect(page.getByText(/You are creating/)).not.toContainText("Untitled");

  await page.goto("/dashboard/campaigns");
  await expect(page.getByText("Spring Sale", { exact: true })).toBeVisible();
  await expect(page.getByText(/Untitled campaignSpring Sale/)).toHaveCount(0);
});

test("an empty name falls back to 'Untitled campaign'", async ({ page }) => {
  const s = await signedIn(page, "p08b");
  await createAdvertiser(page, s);
  await page.goto("/dashboard/campaigns/new");
  await expect(page.locator("#c-name")).toHaveAttribute("placeholder", "Untitled campaign");
  await page.getByRole("button", { name: "Continue to strategy" }).click();
  await page.waitForURL(/\/edit/);
  await expect(page.getByText(/You are creating/)).toContainText("Untitled campaign");
});
