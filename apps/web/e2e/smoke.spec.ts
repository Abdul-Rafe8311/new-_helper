import { expect, test } from "@playwright/test";

test("landing renders the masthead and both calls to action", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));

  await page.goto("/");

  await expect(page).toHaveTitle(/NewsHelper/);
  await expect(page.getByRole("heading", { level: 1, name: "NewsHelper" })).toBeVisible();
  await expect(page.getByText("Your morning, on one page")).toBeVisible();
  await expect(page.getByRole("button", { name: "Try the demo" })).toBeEnabled();
  await expect(page.getByRole("link", { name: "Start my paper" })).toHaveAttribute("href", "/signup");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});

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
