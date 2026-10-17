import { expect, test } from "@playwright/test";

test("landing renders the front page and the three top-bar actions", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  await page.goto("/");

  await expect(page).toHaveTitle(/NewsHelper/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Your morning, on one page");
  const bar = page.getByRole("banner");
  await expect(bar.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
  await expect(bar.getByRole("link", { name: "Start my paper" })).toHaveAttribute("href", "/signup");
  await expect(bar.getByRole("button", { name: "Try the demo" })).toBeEnabled();
  await expect(page.getByText("Sample edition", { exact: true })).toBeVisible();
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

test("landing device preview shows the right frames per width, without console errors", async ({ page, isMobile }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  await page.goto("/");

  const preview = page.locator("figure", { hasText: "Sample edition · preview" });
  await expect(preview).toBeVisible();
  const frame = preview.locator("[aria-hidden='true']").first();
  await expect(frame.getByText("Your morning")).toBeVisible();
  // The tablet's detail panel only exists at tablet width and up.
  const tabletPanel = frame.getByText("Seven outlets covered the story");
  if (isMobile) await expect(tabletPanel).toBeHidden();
  else await expect(tabletPanel).toBeVisible();
  expect(await frame.locator("a, button, [tabindex]").count()).toBe(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});
