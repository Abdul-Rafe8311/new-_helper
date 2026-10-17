import { expect, test } from "@playwright/test";

test("styleguide shows every card variant in both editions", async ({ page }) => {
  await page.goto("/styleguide");
  for (const theme of ["light", "dark"]) {
    const panel = page.locator(`[data-theme-panel="${theme}"]`);
    for (const variant of ["lead", "feature", "standard", "brief", "explore"]) {
      await expect(panel.locator(`article[data-variant="${variant}"]`).first()).toBeVisible();
    }
  }
});

test("signed-in pages send visitors to sign in", async ({ page }) => {
  await page.goto("/today");
  await expect(page).toHaveURL(/\/login\?next=%2Ftoday$/);
  await expect(page.getByRole("heading", { name: "Good morning." })).toBeVisible();
});
