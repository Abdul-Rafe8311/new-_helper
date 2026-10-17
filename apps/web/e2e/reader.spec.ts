import { expect, test, type Page } from "@playwright/test";

const MOCK_API = `http://127.0.0.1:${process.env.MOCK_API_PORT ?? 3199}`;

let counter = 0;

type MockState = {
  events: { type: string; edition_item_id: string; value?: number }[];
  opens: string[];
  pdfDownloads: number;
  eventBatches?: number;
};

/** A signed-in reader whose paper is `edition` ("ready" by default) in the mock API. */
async function signIn(page: Page, seed: { edition?: string; readyAfterMs?: number } = {}): Promise<string> {
  const id = `reader-${process.pid}-${Date.now()}-${counter++}`;
  await page.context().addCookies([{ name: "dp_session", value: id, domain: "127.0.0.1", path: "/" }]);
  const response = await page.request.post(`${MOCK_API}/__seed`, {
    headers: { Cookie: `dp_session=${id}`, "Content-Type": "application/json" },
    data: seed,
  });
  expect(response.ok()).toBe(true);
  return id;
}

async function mockState(page: Page, id: string): Promise<MockState> {
  const response = await page.request.get(`${MOCK_API}/__state`, { headers: { Cookie: `dp_session=${id}` } });
  return (await response.json()) as MockState;
}

// Next keeps pages the reader has left mounted but hidden, so only count what is on screen.
const cards = (page: Page) => page.locator("[data-story]:visible");
const card = (page: Page, headline: string) => cards(page).filter({ hasText: headline });
const LEAD = "Agents are now negotiating their own contracts";
const SECOND = "Inside the startup selling AI interns by the hour";

const noHorizontalScroll = async (page: Page) =>
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

/** The category links: the 240px nav on desktop, the topic pills elsewhere. */
const topics = (page: Page, isMobile: boolean) =>
  isMobile ? page.getByRole("navigation", { name: "Topics" }) : page.getByRole("navigation", { name: "Categories" });

test("read, open a story, save, skip, download the paper, then browse the archive", async ({ page, isMobile }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const id = await signIn(page);

  await page.goto("/today");
  await expect(page.getByRole("heading", { level: 1, name: "For You" })).toBeVisible();
  await expect(cards(page)).toHaveCount(14);

  // categories live in the URL: switching filters at once, and Back restores the whole paper
  await topics(page, isMobile).getByRole("link", { name: "Pavilion End" }).click();
  await expect(page).toHaveURL(/\/today\?section=pavilion-end$/);
  await expect(page.getByRole("heading", { level: 1, name: "Pavilion End" })).toBeVisible();
  await expect(cards(page)).toHaveCount(3);
  await page.goBack();
  await expect(cards(page)).toHaveCount(14);
  await page.goto("/today?section=markets");
  await expect(cards(page)).toHaveCount(3); // a refresh keeps the category

  // save: a separate button on the card, persisted by the API and shown again after a reload
  await page.goto("/today");
  await card(page, LEAD).getByRole("button", { name: "Save" }).click();
  await expect(card(page, LEAD).getByRole("button", { name: "Saved" })).toHaveAttribute("aria-pressed", "true");
  await expect.poll(async () => (await mockState(page, id)).events.map((e) => e.type)).toContain("save");
  await page.reload();
  await expect(card(page, LEAD).getByRole("button", { name: "Saved" })).toHaveAttribute("aria-pressed", "true");

  // open the story page through the card's real link
  await card(page, LEAD).getByRole("link", { name: LEAD }).click();
  await expect(page).toHaveURL(/\/story\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { level: 1, name: LEAD })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await expect(page.getByRole("list", { name: "Key facts" }).or(page.getByRole("heading", { name: "Key facts" }))).toBeVisible();
  await expect(page.getByRole("complementary", { name: "Sources" }).getByRole("link")).toHaveCount(2);
  await expect(page.getByTestId("photo-stack").locator("img")).toHaveCount(4);
  await expect(page.getByRole("button", { name: "Saved" })).toHaveAttribute("aria-pressed", "true");

  // the gallery: keyboard navigation, Escape, and focus returns to the button
  const viewPhotos = page.getByRole("button", { name: /View photos/ });
  await viewPhotos.click();
  const gallery = page.getByRole("dialog");
  await expect(gallery.getByRole("status")).toContainText("Photo 1 of 4");
  await page.keyboard.press("ArrowRight");
  await expect(gallery.getByRole("status")).toContainText("Photo 2 of 4");
  await expect(gallery.getByRole("status")).toContainText("Credit:");
  await page.keyboard.press("Escape");
  await expect(gallery).toBeHidden();
  await expect(viewPhotos).toBeFocused();

  // feedback from the story page reaches the API
  await page.getByRole("button", { name: "More like this" }).click();
  await expect.poll(async () => (await mockState(page, id)).events.map((e) => e.type)).toContain("more_like");

  // read original: a new tab through /api/r/{id}, which logs the open and redirects
  const [popup] = await Promise.all([
    page.waitForEvent("popup"),
    page.context().waitForEvent("request", (request) => /\/api\/r\/[0-9a-f-]{36}$/.test(request.url())),
    page.getByRole("link", { name: "Read original", exact: true }).first().click(),
  ]);
  await popup.waitForLoadState();
  expect(popup.url()).toContain("/__original/1");
  await popup.close();
  await expect.poll(async () => (await mockState(page, id)).opens.length).toBe(1);

  // back to the edition, then skip a story from its card
  await page.getByRole("link", { name: "Back to edition" }).click();
  await expect(page).toHaveURL(/\/paper\/|\/today/);
  await expect(cards(page)).toHaveCount(14);
  await card(page, SECOND).getByRole("button", { name: "Skip" }).click();
  await expect(cards(page)).toHaveCount(13);
  await expect(page.getByRole("status").filter({ hasText: "Story skipped" })).toBeVisible();
  await expect.poll(async () => (await mockState(page, id)).events.map((e) => e.type)).toContain("skip");

  // the paper as a PDF
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Download newspaper" }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/\.pdf$/);
  expect((await mockState(page, id)).pdfDownloads).toBe(1);

  // archive: a grid of past editions that keeps loading as the reader scrolls
  await page.goto("/archive");
  const editions = page.getByRole("list", { name: "Past editions" }).locator("[data-story-link]");
  await expect.poll(() => editions.count()).toBeGreaterThanOrEqual(20);
  // it keeps loading pages (20 at a time) until the archive runs out
  await expect(async () => {
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await expect(page.getByText("That's everything.")).toBeVisible({ timeout: 1000 });
  }).toPass();
  await expect(editions).toHaveCount(45);
  await editions.first().click();
  await expect(page).toHaveURL(/\/archive\/\d{4}-\d{2}-\d{2}$/);
  await expect(page.getByRole("heading", { level: 1, name: "For You" })).toBeVisible();
  await expect(cards(page).first()).toBeVisible();
  expect(errors).toEqual([]);
});

test("a broken picture falls back to a category-coloured panel", async ({ page }) => {
  await signIn(page);
  await page.goto("/today");
  await expect(card(page, "Why every SaaS pricing page just changed").getByTestId("image-fallback")).toBeVisible();
  // pictureless stories get the same deliberate fallback
  await expect(card(page, "Rupee steadies as imports slow").getByTestId("image-fallback")).toBeVisible();
});

test("cards lift on hover with a fine pointer, and stay still with reduced motion", async ({ page, isMobile }) => {
  test.skip(isMobile, "hover needs a fine pointer");
  await signIn(page);
  await page.goto("/today");
  const surface = card(page, SECOND).locator(".story-card__surface");
  await expect(surface).toBeVisible();
  const transform = () => surface.evaluate((el) => getComputedStyle(el).transform);
  expect(await transform()).toBe("none");
  await surface.hover();
  await expect.poll(transform).toBe("matrix(1.025, 0, 0, 1.025, 0, 0)");
  await page.mouse.move(0, 0);
  await expect.poll(transform).toBe("none");

  await page.emulateMedia({ reducedMotion: "reduce" });
  await surface.hover();
  await page.waitForTimeout(250);
  expect(await transform()).toBe("none");
});

test("keyboard shortcuts drive the feed", async ({ page, isMobile }) => {
  test.skip(isMobile, "keyboard shortcuts are for desktop");
  const id = await signIn(page);
  await page.goto("/today");
  await expect(cards(page)).toHaveCount(14);

  await page.keyboard.press("j");
  await expect(cards(page).nth(0)).toHaveAttribute("data-focused", "true");
  await expect(cards(page).nth(0).getByRole("link")).toBeFocused();
  await page.keyboard.press("j");
  await expect(cards(page).nth(1)).toHaveAttribute("data-focused", "true");
  await page.keyboard.press("k");
  await expect(cards(page).nth(0)).toHaveAttribute("data-focused", "true");

  await page.keyboard.press("s");
  await expect(page.getByRole("status").filter({ hasText: "Saved for later" })).toBeVisible();
  await page.keyboard.press("m");
  await page.keyboard.press("j");
  await page.keyboard.press("x");
  await expect(cards(page)).toHaveCount(13);
  await page.keyboard.press("Shift+A");
  await expect(page.getByRole("img", { name: "Unread" })).toHaveCount(0);

  await expect
    .poll(async () => (await mockState(page, id)).events.map((e) => e.type))
    .toEqual(expect.arrayContaining(["save", "more_like", "skip", "mark_read"]));

  // saved stories show up on /saved, and un-saving removes them
  await page.goto("/saved");
  await expect(cards(page)).toHaveCount(1);
  await expect(cards(page).first()).toContainText(LEAD);
  await cards(page).first().getByRole("button", { name: "Saved" }).click();
  await expect(cards(page)).toHaveCount(0);
  await expect(page.getByText("Nothing saved yet.")).toBeVisible();
});

test("impressions and dwell time are batched to the API", async ({ page }) => {
  const id = await signIn(page);
  await page.goto("/today");
  await expect(cards(page)).toHaveCount(14);
  await page.waitForTimeout(2500);
  await page.goto("/settings"); // a full navigation: whatever is queued must go out with the beacon

  await expect
    .poll(async () => (await mockState(page, id)).events.map((e) => e.type), { timeout: 20_000, intervals: [1000] })
    .toEqual(expect.arrayContaining(["impression", "dwell"]));
  expect((await mockState(page, id)).eventBatches).toBeLessThanOrEqual(2);
});

test("a paper still on the press shows the printing press and appears when ready", async ({ page }) => {
  await signIn(page, { edition: "pending", readyAfterMs: 3000 });
  await page.goto("/today");
  await expect(page.getByRole("heading", { name: "Your paper is on the press" })).toBeVisible();
  await expect(page.getByTestId("printing-press")).toBeVisible();
  await expect(cards(page)).toHaveCount(14, { timeout: 15_000 });
});

test("with no paper yet, the reader can ask for one", async ({ page }) => {
  await signIn(page, { edition: "none" });
  await page.goto("/today");
  await expect(page.getByRole("heading", { name: "No paper yet today" })).toBeVisible();
  await page.getByRole("button", { name: "Print today's paper" }).click();
  await expect(page.getByRole("heading", { name: "Your paper is on the press" })).toBeVisible();
  await expect(cards(page)).toHaveCount(14, { timeout: 15_000 });
});

test("the layout adapts without horizontal overflow", async ({ page, isMobile }) => {
  await signIn(page);
  for (const [width, height] of isMobile ? [[390, 844]] : [[1440, 900], [1280, 800], [768, 1024]]) {
    await page.setViewportSize({ width, height });
    await page.goto("/today");
    await expect(cards(page)).toHaveCount(14);
    await noHorizontalScroll(page);
    const first = await cards(page).nth(0).boundingBox();
    const second = await cards(page).nth(1).boundingBox();
    const third = await cards(page).nth(2).boundingBox();
    const nav = page.getByRole("navigation", { name: "Categories" });
    if (width >= 1280) {
      // sidebar 240px; content starts near 272px; the lead row is 7+5 columns, then thirds
      expect((await nav.boundingBox())?.width).toBeCloseTo(240 - 0, -1);
      expect(first!.x).toBeGreaterThan(250);
      expect(first!.width).toBeGreaterThan(second!.width);
      expect(Math.abs(third!.y - first!.y)).toBeGreaterThan(200); // the third card starts row two
    } else if (width >= 768) {
      await expect(nav).toBeHidden(); // compact: topic pills and a menu
      expect(Math.abs(first!.width - second!.width)).toBeGreaterThan(100); // lead spans both columns
      expect(second!.width).toBeCloseTo(third!.width, -1);
    } else {
      expect(first!.width).toBeGreaterThan(330); // one column
      await expect(page.getByRole("button", { name: "Download newspaper" })).toBeVisible();
    }
  }
});

test("on small screens the menu opens a drawer with the categories", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await signIn(page);
  await page.goto("/today");
  await page.getByRole("button", { name: "Open menu" }).click();
  const drawer = page.getByRole("dialog");
  await drawer.getByRole("link", { name: "Science" }).click();
  await expect(page).toHaveURL(/section=science/);
  await expect(drawer).toBeHidden();
  await expect(cards(page)).toHaveCount(2);
});

test("signed-out visitors are sent to sign in from every reader page", async ({ page }) => {
  for (const path of ["/saved", "/settings", "/paper/2026-10-01", "/archive/2026-10-01", "/story/00000000-0000-4000-a000-000000000001"]) {
    await page.goto(path);
    await expect(page).toHaveURL(new RegExp(`/login\\?next=${encodeURIComponent(path).replaceAll("/", "%2F")}`));
  }
});
