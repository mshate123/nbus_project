import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E configuration for nbus ledger.
 *
 * Assumes the full Docker stack is running:
 *   docker-compose --profile app up --build
 *
 * Frontend at http://localhost:3000 (nginx proxies /api/* to backend).
 */
export default defineConfig({
  // E2E config and specs live together under the repository-level e2e directory.
  testDir: ".",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: "html",
  timeout: 30_000,

  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
