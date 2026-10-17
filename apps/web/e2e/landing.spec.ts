import { expect, test, type Page } from "@playwright/test";

function watchConsole(page: Page): string[] {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  return errors;
}

const noSideScroll = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);

test("landing: three sections, real destinations, no console errors", async ({ page }) => {
  const errors = watchConsole(page);
  await page.goto("/");
  await expect(page).toHaveTitle(/NewsHelper/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("One daily paper.");
  await expect(page.locator("main section")).toHaveCount(3);
  const nav = page.getByRole("banner");
  await expect(nav.getByRole("link", { name: "Build my paper" })).toHaveAttribute("href", "/signup");
  await expect(page.getByRole("link", { name: "Open my paper" })).toHaveAttribute("href", "/today");
  expect(await noSideScroll(page)).toBe(true);
  expect(errors).toEqual([]);
});

test("landing: orbit portraits stay upright and label on focus", async ({ page, isMobile }) => {
  await page.goto("/");
  const science = page.getByRole("button", { name: "Technology desk" });
  if (!isMobile) await expect(science).toBeVisible();
  // Upright: the slot is only ever translated and scaled, never rotated.
  const skew = await page.locator(".lp-slot").first().evaluate((el) => {
    const m = new DOMMatrixReadOnly(getComputedStyle(el).transform);
    return Math.abs(m.b) + Math.abs(m.c);
  });
  expect(skew).toBeLessThan(0.001);
  await science.focus();
  await expect(science.locator(".lp-label")).toHaveCSS("opacity", "1");
  await expect(page.locator(".lp-cast")).toHaveAttribute("data-focus", "true");
});

test("landing: the manifesto is readable and the orbit scatters on scroll", async ({ page, isMobile }) => {
  await page.goto("/");
  await expect(page.locator(".lp-sr")).toContainText("brings the stories you care about into one daily edition");
  await page.locator("#how-it-works").scrollIntoViewIfNeeded();
  await page.evaluate(() => window.scrollTo(0, document.querySelector("#how-it-works")!.getBoundingClientRect().top + window.scrollY - 100));
  await expect(page.locator(".lp-cast")).toHaveAttribute("data-scattered", "true");
  const progress = await page.locator(".lp-cast").evaluate((el) => Number(el.style.getPropertyValue("--p")));
  expect(progress).toBeGreaterThan(0.5);
  expect(await noSideScroll(page)).toBe(true);
  void isMobile;
});

test("landing: preview chips select a view and hide the others", async ({ page }) => {
  await page.goto("/");
  await page.locator("#read-your-way").scrollIntoViewIfNeeded();
  const pdf = page.getByRole("button", { name: "Newspaper PDF" });
  await pdf.click();
  await expect(pdf).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#lp-panel-pdf")).toHaveAttribute("data-active", "true");
  await expect(page.locator("#lp-panel-web")).toHaveAttribute("aria-hidden", "true");
  await expect(page.getByRole("heading", { name: "Past editions" })).toBeHidden();
  await page.getByRole("button", { name: "Archive" }).click();
  await expect(page.getByRole("heading", { name: "Past editions" })).toBeVisible();
  await expect(page.locator("#lp-panel-pdf [href], #lp-panel-pdf button")).toHaveCount(0);
});

test("landing: the preview carries a decorative pixel-scan canvas", async ({ page }) => {
  await page.goto("/");
  const scan = page.locator(".lp-phone canvas");
  await expect(scan).toHaveCount(1);
  await expect(scan).toHaveAttribute("aria-hidden", "true");
  await expect(scan).toHaveCSS("pointer-events", "none");
});

test.describe("reduced motion", () => {
  test.use({ reducedMotion: "reduce" });
  test("nothing is pinned or rotating, and the statement is fully lit", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator(".lp-cast")).toHaveCSS("animation-name", "none");
    await expect(page.locator(".lp-ryw__pin")).toHaveCSS("position", "static");
    const wp = await page.locator(".lp-word").first().evaluate((el) => getComputedStyle(el).color);
    expect(wp).toMatch(/245|0\.9607/);
  });
});
