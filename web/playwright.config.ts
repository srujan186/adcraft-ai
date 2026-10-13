import { defineConfig, devices } from "@playwright/test";

/**
 * Browser tests for the web app. They drive the real UI against a running API:
 *   API  : api/ on E2E_API_URL (default http://127.0.0.1:8000) with ENV=development
 *   Web  : started here (or reused) on http://localhost:3000
 * Each test signs up its own user through the API, so no seed data is assumed.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  // Against `next dev`, the first visit to a changed page compiles it on demand; parallel cold
  // compiles made 5 s assertion waits flaky. Two workers and 10 s waits keep the suite stable.
  expect: { timeout: 10_000 },
  workers: 2,
  fullyParallel: false,
  reporter: [["list"]],
  use: { baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "pnpm dev",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
