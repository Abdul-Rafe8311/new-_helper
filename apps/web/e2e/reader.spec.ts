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
const stories = (page: Page) => page.locator("[data-story]:visible");
const story = (page: Page, headline: string) => stories(page).filter({ hasText: headline });
const LEAD = "Agents are now negotiating their own contracts";

test("read, skip, open the original, download the PDF, then browse the archive", async ({ page, isMobile }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const id = await signIn(page);

  await page.goto("/today");
  await expect(page.getByRole("heading", { level: 1, name: "The Rafe Courier" })).toBeVisible();
  await expect(stories(page)).toHaveCount(14);

  // sections with unread counts (the panel on desktop, tabs on phones)
  const sections = isMobile ? page.getByRole("tablist", { name: "Sections" }) : page.getByRole("list", { name: "Sections" });
  await expect(sections.getByText("The Agent Economy")).toBeVisible();
  await expect(sections.getByRole(isMobile ? "tab" : "button", { name: /The Agent Economy/ })).toContainText("4");

  // expand in place: full summary, key facts, why chip with a score breakdown
  await story(page, LEAD).getByRole("button", { name: LEAD }).click();
  const lead = story(page, LEAD);
  await expect(lead.getByRole("list", { name: "Key facts" })).toContainText("Fact one of story 1");
  await expect(lead.getByRole("button", { name: /Why you're seeing this/ })).toBeVisible();
  await expect(sections.getByRole(isMobile ? "tab" : "button", { name: /The Agent Economy/ })).toContainText("3");

  // skip with an undo toast
  await lead.getByRole("button", { name: "Skip" }).click();
  await expect(stories(page)).toHaveCount(13);
  await expect(page.getByRole("status").filter({ hasText: "Story skipped" })).toBeVisible();

  // read original: a new tab through /api/r/{id}, which logs the open and redirects
  const second = story(page, "Inside the startup selling AI interns by the hour");
  await second.getByRole("button", { name: /Inside the startup/ }).click();
  const [popup] = await Promise.all([
    page.waitForEvent("popup"),
    page.context().waitForEvent("request", (request) => /\/api\/r\/[0-9a-f-]{36}$/.test(request.url())),
    second.getByRole("link", { name: "Read original" }).click(),
  ]);
  await popup.waitForLoadState();
  expect(popup.url()).toContain("/__original/2");
  await popup.close();
  await expect.poll(async () => (await mockState(page, id)).opens.length).toBe(1);

  // the skip reached the API on the urgent flush
  await expect.poll(async () => (await mockState(page, id)).events.map((e) => e.type)).toContain("skip");

  // PDF download
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Download PDF" }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/\.pdf$/);
  expect((await mockState(page, id)).pdfDownloads).toBe(1);

  // archive: the left panel lists past editions and keeps loading as it scrolls
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Archive" }).click();
  await expect(page).toHaveURL(/\/archive$/);
  if (isMobile) await page.getByRole("button", { name: "Show past editions" }).click();
  const editions = page.getByRole("list", { name: "Past editions" }).getByRole("link", { name: /stories/ });
  await expect(editions).toHaveCount(20);
  await editions.last().scrollIntoViewIfNeeded();
  await expect(editions).toHaveCount(40);
  await editions.first().click();
  await expect(page).toHaveURL(/\/archive\/\d{4}-\d{2}-\d{2}$/);
  await expect(page.getByRole("heading", { level: 1, name: "The Rafe Courier" })).toBeVisible();
  // the mock reuses story ids on every date, so the story skipped above is skipped here too
  await expect(stories(page)).toHaveCount(13);
  expect(errors).toEqual([]);
});

test("the view toggle switches between list, cards and newspaper and remembers the choice", async ({ page }) => {
  await signIn(page);
  await page.goto("/today");
  await expect(stories(page)).toHaveCount(14);

  await page.getByRole("button", { name: "List view" }).click();
  await expect(page.getByRole("button", { name: "List view" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("p.line-clamp-3")).toHaveCount(0); // the cards are gone
  await expect(page.getByRole("img", { name: "Unread" })).toHaveCount(14);
  await expect(story(page, LEAD).getByText("This is the longer summary of story 1", { exact: false })).toHaveCSS(
    "text-overflow",
    "ellipsis",
  );

  await page.getByRole("button", { name: "Newspaper view" }).click();
  await expect(page.getByRole("heading", { name: "Three things to know" })).toBeVisible();
  await expect(page.locator('article[data-variant="lead"]')).toHaveCount(1);
  await expect(page.getByRole("heading", { name: "In brief" })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("button", { name: "Newspaper view" })).toHaveAttribute("aria-pressed", "true");
});

test("keyboard shortcuts drive the reader", async ({ page, isMobile }) => {
  test.skip(isMobile, "keyboard shortcuts are for desktop");
  const id = await signIn(page);
  await page.goto("/today");
  await expect(stories(page)).toHaveCount(14);

  await page.keyboard.press("j");
  await expect(stories(page).nth(0)).toHaveAttribute("data-focused", "true");
  await page.keyboard.press("j");
  await expect(stories(page).nth(1)).toHaveAttribute("data-focused", "true");
  await page.keyboard.press("k");
  await expect(stories(page).nth(0)).toHaveAttribute("data-focused", "true");

  await page.keyboard.press("s");
  await expect(page.getByRole("status").filter({ hasText: "Saved for later" })).toBeVisible();
  await page.keyboard.press("m");
  await page.keyboard.press("j");
  await page.keyboard.press("x");
  await expect(stories(page)).toHaveCount(13);

  await page.keyboard.press("Shift+A");
  await expect(page.getByRole("img", { name: "Unread" })).toHaveCount(0);

  await expect
    .poll(async () => (await mockState(page, id)).events.map((e) => e.type))
    .toEqual(expect.arrayContaining(["save", "more_like", "skip", "mark_read"]));

  // typing in the search box must not trigger shortcuts
  await page.getByRole("searchbox", { name: "Search this paper" }).fill("sxj");
  await expect(page.getByText("Nothing in this paper matches your search.")).toBeVisible();

  // saved stories show up on /saved
  await page.getByRole("searchbox", { name: "Search this paper" }).fill("");
  await page.goto("/saved");
  await expect(stories(page)).toHaveCount(1);
  await expect(stories(page).first()).toContainText(LEAD);
});

test("impressions and dwell time are batched to the API", async ({ page }) => {
  const id = await signIn(page);
  await page.goto("/today");
  await expect(stories(page)).toHaveCount(14);
  await page.waitForTimeout(2500); // long enough on screen for an impression and some dwell
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Settings" }).click();

  // events go out in one batch every 10s; leaving the page does not lose them
  await expect
    .poll(async () => (await mockState(page, id)).events.map((e) => e.type), { timeout: 20_000, intervals: [1000] })
    .toEqual(expect.arrayContaining(["impression", "dwell"]));
  const state = await mockState(page, id);
  expect(state.eventBatches).toBeLessThanOrEqual(2);
});

test("a paper still on the press shows the printing press and appears when ready", async ({ page }) => {
  await signIn(page, { edition: "pending", readyAfterMs: 3000 });
  await page.goto("/today");
  await expect(page.getByRole("heading", { name: "Your paper is on the press" })).toBeVisible();
  await expect(page.getByTestId("printing-press")).toBeVisible();
  await expect(stories(page)).toHaveCount(14, { timeout: 15_000 });
});

test("with no paper yet, the reader can ask for one", async ({ page }) => {
  await signIn(page, { edition: "none" });
  await page.goto("/today");
  await expect(page.getByRole("heading", { name: "No paper yet today" })).toBeVisible();
  await page.getByRole("button", { name: "Print today's paper" }).click();
  await expect(page.getByRole("heading", { name: "Your paper is on the press" })).toBeVisible();
  await expect(stories(page)).toHaveCount(14, { timeout: 15_000 });
});

test("the shell adapts: icon rail on desktop, tab bar and section tabs on phones", async ({ page, isMobile }) => {
  await signIn(page);
  await page.goto("/today");
  await expect(stories(page)).toHaveCount(14);
  const nav = page.getByRole("navigation", { name: "Main" });
  const box = await nav.boundingBox();
  const viewport = page.viewportSize();
  expect(box && viewport).toBeTruthy();
  if (isMobile) {
    expect(box!.y + box!.height).toBeCloseTo(viewport!.height, -1);
    expect(box!.width).toBeCloseTo(viewport!.width, -1);
    await expect(page.getByRole("tablist", { name: "Sections" })).toBeVisible();
    await expect(page.getByRole("list", { name: "Sections" })).toBeHidden();
    await page.getByRole("button", { name: "Toggle sections panel" }).click();
    await expect(page.getByRole("complementary", { name: "Sections" })).toBeVisible();
  } else {
    expect(box!.x).toBe(0);
    expect(box!.width).toBe(60);
    await expect(page.getByRole("list", { name: "Sections" })).toBeVisible();
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("signed-out visitors are sent to sign in from every reader page", async ({ page }) => {
  for (const path of ["/saved", "/settings", "/paper/2026-10-01", "/archive/2026-10-01"]) {
    await page.goto(path);
    await expect(page).toHaveURL(new RegExp(`/login\\?next=${encodeURIComponent(path).replaceAll("/", "%2F")}`));
  }
});
