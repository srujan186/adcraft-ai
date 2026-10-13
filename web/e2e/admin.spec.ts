import { expect, test } from "@playwright/test";

import { signedIn, signedInAs } from "./helpers";

// Requires the local API to run with ALLOW_SIMULATION=true and ADMIN_EMAILS including this login.
const ADMIN = "e2e-admin@acme.io";

test("non-admins don't see the admin page or menu entry", async ({ page }) => {
  await signedIn(page, "p01user");
  await page.goto("/dashboard/admin");
  await expect(page.getByText(/could not be found/i)).toBeVisible();
  await page.goto("/dashboard");
  await page.getByRole("button", { name: /E2E Co/ }).click();
  await expect(page.getByRole("menuitem", { name: "Admin" })).toHaveCount(0);
});

test("an admin can open the page from the menu and simulate history", async ({ page }) => {
  await signedInAs(page, ADMIN);
  await page.goto("/dashboard");
  await page.getByRole("button", { name: /E2E Co/ }).click();
  await page.getByRole("menuitem", { name: "Admin" }).click();
  await page.waitForURL("**/dashboard/admin");
  await expect(page.getByText("Continuous delivery")).toBeVisible();

  await page.fill("#admin-days", "3");
  await page.click("#admin-simulate");
  await expect(page.locator("#admin-notice")).toContainText("Adding 3 days of delivery history");
});
