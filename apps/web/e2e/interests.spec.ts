import { expect, test, type Page } from "@playwright/test";

const MOCK_API = `http://127.0.0.1:${process.env.MOCK_API_PORT ?? 3199}`;
let counter = 0;

async function signIn(page: Page): Promise<string> {
  const id = `interests-${process.pid}-${Date.now()}-${counter++}`;
  await page.context().addCookies([{ name: "dp_session", value: id, domain: "127.0.0.1", path: "/" }]);
  const response = await page.request.post(`${MOCK_API}/__seed`, {
    headers: { Cookie: `dp_session=${id}`, "Content-Type": "application/json" },
    data: {},
  });
  expect(response.ok()).toBe(true);
  return id;
}

/** Test-only trigger for the nightly learn stage (the incremental one runs on its own). */
const runNightly = (page: Page, id: string) =>
  page.request.post(`${MOCK_API}/__learn`, { headers: { Cookie: `dp_session=${id}` } });

const cards = (page: Page) => page.locator("[data-story]:visible");
const card = (page: Page, headline: string) => cards(page).filter({ hasText: headline });
const hydrated = (page: Page) =>
  page.waitForFunction(() =>
    Object.keys(document.querySelector("[data-story]") ?? {}).some((key) => key.startsWith("__reactFiber")),
  );

const SKIPPED = "Inside the startup selling AI interns by the hour"; // Artificial Intelligence
const DISLIKED = "Central banks signal a synchronised pause"; // Markets

test("skips and dislikes on /today show up on /interests after the learner runs", async ({ page }) => {
  const id = await signIn(page);
  await page.goto("/today");
  await hydrated(page);

  await card(page, SKIPPED).getByRole("button", { name: "Skip" }).click();
  await expect(cards(page)).toHaveCount(13);
  await card(page, DISLIKED).getByRole("button", { name: "Less like this" }).click();
  await expect(card(page, DISLIKED).getByRole("button", { name: "Less like this" })).toHaveAttribute("aria-pressed", "true");
  // events are batched every 10s; leaving the page flushes them
  await page.goto("/interests");
  await expect(page.getByRole("heading", { level: 1, name: "What Daybreak has learned about you" })).toBeVisible();
  await expect.poll(async () => (await page.request.get(`${MOCK_API}/__state`, { headers: { Cookie: `dp_session=${id}` } }).then((r) => r.json())).events.length).toBeGreaterThan(1);

  await page.reload();
  const before = await page.getByTestId("timeline").getByRole("listitem").count();
  expect(await page.getByText("Lowered Artificial Intelligence").count()).toBe(0);

  // the less_like was strong: the blocked list updated without waiting for the night
  await expect(page.getByTestId("blocked-list").getByText("Markets")).toBeVisible();

  expect((await runNightly(page, id)).ok()).toBe(true);
  await page.reload();
  await expect(page.getByText("Lowered Artificial Intelligence: you skipped a Artificial Intelligence story")).toBeVisible();
  expect(await page.getByTestId("timeline").getByRole("listitem").count()).toBeGreaterThan(before);

  // unblock it again
  await page.getByRole("button", { name: "Unblock Markets" }).click();
  await expect(page.getByText("Nothing is blocked.")).toBeVisible();
});

test("sliders are keyboard operable and every change is logged; reset asks first", async ({ page }) => {
  await signIn(page);
  await page.goto("/interests");
  await expect(page.getByRole("heading", { level: 1, name: "What Daybreak has learned about you" })).toBeVisible();

  const cricket = page.getByRole("slider", { name: /Cricket/ });
  await cricket.focus();
  await expect(cricket).toBeFocused();
  await cricket.press("ArrowRight");
  await expect(page.getByText("Saved Cricket.")).toBeVisible();
  await expect(page.getByTestId("timeline").getByText("You set Cricket to 85%")).toBeVisible();

  // chips are buttons: pin and remove
  await page.getByRole("button", { name: "Pin Babar Azam" }).click();
  await expect(page.getByRole("button", { name: "Unpin Babar Azam" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Remove Babar Azam" }).click();
  await expect(page.getByRole("button", { name: /Babar Azam/ })).toHaveCount(0);

  // reset: nothing happens until the reader confirms
  await page.getByRole("button", { name: "Reset what it has learned" }).click();
  await expect(page.getByRole("group", { name: "Confirm reset" })).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByRole("button", { name: /Lahore Qalandars/ }).first()).toBeVisible();
  await page.getByRole("button", { name: "Reset what it has learned" }).click();
  await page.getByRole("button", { name: "Yes, reset" }).click();
  await expect(page.getByText("Reset to your onboarding choices")).toBeVisible();
  await expect(page.getByRole("button", { name: /Lahore Qalandars/ })).toHaveCount(0);
  await expect(page.getByTestId("timeline").getByText("You set Cricket to 85%")).toBeVisible(); // history stays
});

for (const [name, width, height] of [
  ["1440", 1440, 1000],
  ["390", 390, 844],
] as const) {
  test(`screenshot of /interests at ${width}px`, async ({ page, isMobile }) => {
    test.skip(isMobile, "the viewport is set here; one project is enough");
    await signIn(page);
    await page.setViewportSize({ width, height });
    await page.goto("/interests");
    await expect(page.getByRole("heading", { level: 1, name: "What Daybreak has learned about you" })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: `../../docs/screenshots/interests-${name}.png`, fullPage: true });
  });
}
