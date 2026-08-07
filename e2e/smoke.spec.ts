import { expect, test } from "@playwright/test";

/** Smoke test: the app can load and display the persisted rate schedule. */
test("loads the ledger and shows the rate schedule", async ({ page }) => {
  // The rate schedule is seeded by the database migration, making this a
  // deterministic UI -> API -> database smoke path without test-only data.
  const ratesResponse = page.waitForResponse(
    (response) => response.url().endsWith("/api/rate-schedule") && response.ok(),
  );

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "nbus Ledger" })).toBeVisible();

  await page.getByRole("button", { name: "Rate Schedule" }).click();
  await expect(ratesResponse).resolves.toBeTruthy();
  await expect(
    page.getByRole("heading", { name: "Interest Rate Schedule" }),
  ).toBeVisible();
  await expect(page.locator("tbody tr")).not.toHaveCount(0);
});
