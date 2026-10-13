import { expect, test } from "@playwright/test";

import { signedIn } from "./helpers";

// P0-2: with no LLM key the agent used to answer with canned "facts" about audiences the user
// didn't have. It must now say it's unavailable and offer help articles only.
test("without an LLM key the agent says it's unavailable and links help articles", async ({ page }) => {
  await signedIn(page, "p02");
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Ask Agent" }).click();

  await page.getByRole("button", { name: "How does CTV advertising work?" }).click();

  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText(/The assistant isn't available right now/)).toBeVisible();
  const link = dialog.getByRole("link", { name: "How streaming-TV advertising works" });
  await expect(link).toHaveAttribute("href", "/help/how-ctv-advertising-works");
  await expect(dialog.getByText(/Visitors|highest-intent/)).toHaveCount(0);
});
