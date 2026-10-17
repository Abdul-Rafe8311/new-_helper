import { expect, test, type Page } from "@playwright/test";

const MOCK_API = `http://127.0.0.1:${process.env.MOCK_API_PORT ?? 3199}`;

let counter = 0;

/** A signed-in reader with their own slice of the mock API's state. */
async function signIn(page: Page): Promise<string> {
  const id = `e2e-${process.pid}-${Date.now()}-${counter++}`;
  await page.context().addCookies([{ name: "dp_session", value: id, domain: "127.0.0.1", path: "/" }]);
  return id;
}

async function mockState(page: Page, id: string) {
  const response = await page.request.get(`${MOCK_API}/__state`, { headers: { Cookie: `dp_session=${id}` } });
  return (await response.json()) as {
    steps: Record<string, Record<string, unknown>>;
    answers: Record<string, boolean>;
    completeCalls: number;
    completed: boolean;
  };
}

/** The card for headline `n`; while the previous card animates out, two cards briefly coexist. */
const card = (page: Page, n: number) => page.getByTestId("taste-card").filter({ hasText: `Headline number ${n}:` });

async function noHorizontalScroll(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}

test("a new reader completes onboarding and lands on their paper", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const id = await signIn(page);

  // 1. Name your paper
  await page.goto("/onboarding");
  await expect(page.getByRole("heading", { name: "Name your paper" })).toBeVisible();
  const preview = page.getByTestId("masthead-preview");
  await expect(preview.getByRole("heading", { level: 1 })).toHaveText("The Rafe Morning");
  await page.getByLabel("Paper name").fill("The Lahore Ledger");
  await expect(preview.getByRole("heading", { level: 1 })).toHaveText("The Lahore Ledger");
  await page.getByLabel("Your city").fill("Lahore");
  await expect(preview).toContainText("Printed for Lahore");
  await noHorizontalScroll(page);
  await page.getByRole("button", { name: "Continue", exact: true }).click();

  // 2. Pick your beats (at least three)
  await expect(page.getByRole("heading", { name: "Pick your beats" })).toBeVisible();
  const next = page.getByRole("button", { name: "Continue", exact: true });
  await expect(next).toBeDisabled();
  await page.getByRole("button", { name: "Cricket", exact: true }).click();
  await expect(page.getByTestId("deeper-cricket")).toBeVisible();
  await page.getByRole("button", { name: "PSL" }).click();
  await page.getByRole("button", { name: "Artificial Intelligence" }).click();
  await expect(next).toBeDisabled();
  await expect(page.getByRole("status").filter({ hasText: "Pick 1 more" })).toBeVisible();
  await page.getByRole("button", { name: "Formula 1" }).click();
  await expect(next).toBeEnabled();
  await noHorizontalScroll(page);
  await next.click();

  // 3. In your own words
  await expect(page.getByRole("heading", { name: "In your own words" })).toBeVisible();
  await page.getByLabel("What should your paper be about?").fill("I run an agency, follow AI agents and PSL, skip celebrity gossip");
  await expect(next).toBeDisabled(); // typed but not read yet
  await page.getByRole("button", { name: "Show me what you heard" }).click();
  await expect(page.getByText("We heard:")).toBeVisible();
  await expect(page.getByRole("list", { name: "What we heard" }).getByText("PSL")).toBeVisible();
  await expect(page.getByRole("list", { name: "What to skip" })).toContainText("celebrity gossip");
  await page.getByRole("button", { name: "Remove PSL" }).click();
  await expect(page.getByRole("list", { name: "What we heard" }).getByText("PSL", { exact: true })).toHaveCount(0);
  await expect(next).toBeEnabled();
  await next.click();

  // 4. Taste test: tap a few, use the keyboard for the rest
  await expect(page.getByRole("heading", { name: "A quick taste test" })).toBeVisible();
  await expect(card(page, 1)).toBeVisible();
  await page.getByRole("button", { name: "Interested" }).click();
  await expect(card(page, 2)).toBeVisible();
  await page.getByRole("button", { name: "Not for me" }).click();
  await expect(card(page, 3)).toBeVisible();
  for (let i = 3; i <= 12; i++) {
    await expect(card(page, i)).toBeVisible();
    await page.getByRole("group", { name: "Headline taste test" }).focus();
    await page.keyboard.press(i % 2 ? "ArrowRight" : "ArrowLeft");
  }
  await expect(page.getByText("Got it.")).toBeVisible();
  await next.click();

  // 5. How do you read
  await expect(page.getByRole("heading", { name: "How do you read?" })).toBeVisible();
  await page.getByRole("radio", { name: /20 min/ }).click();
  await page.getByRole("radio", { name: /Deep dives/ }).click();
  const surprise = page.getByRole("switch", { name: /outside my bubble/ });
  await expect(surprise).toHaveAttribute("aria-checked", "true");
  await surprise.click();
  await expect(surprise).toHaveAttribute("aria-checked", "false");
  await page.getByRole("button", { name: "Print my first edition" }).click();

  // 6. Finale: the press runs, then the reader lands on /today
  await expect(page.getByRole("heading", { name: "Printing your first edition" })).toBeVisible();
  await expect(page.getByTestId("printing-press")).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: /Gathering|Choosing|Writing|Typesetting|Warming/ })).toBeVisible();
  await expect(page).toHaveURL(/\/today$/, { timeout: 20_000 });

  // everything was saved along the way
  const saved = await mockState(page, id);
  expect(saved.completed).toBe(true);
  expect(saved.steps["1"]).toMatchObject({ paper_name: "The Lahore Ledger", city: "Lahore" });
  expect(saved.steps["2"]).toMatchObject({ topics: ["cricket", "ai", "f1"], deeper: { cricket: ["PSL"] } });
  expect(saved.steps["3"]).toMatchObject({ parsed: { keywords: ["AI agents"] } });
  expect(saved.steps["5"]).toEqual({ reading_minutes: 20, depth: "deep", surprise_me: false });
  expect(Object.keys(saved.answers)).toHaveLength(12);
  expect(Object.values(saved.answers).filter(Boolean)).toHaveLength(6);
  expect(errors).toEqual([]);
});

test("a refresh resumes where the reader left off", async ({ page }) => {
  await signIn(page);
  await page.goto("/onboarding");
  await page.getByLabel("Paper name").fill("The Resume Review");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  for (const topic of ["World", "Business", "Science"]) await page.getByRole("button", { name: topic, exact: true }).click();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByRole("heading", { name: "In your own words" })).toBeVisible();

  await page.reload();

  await expect(page.getByRole("heading", { name: "In your own words" })).toBeVisible();
  await page.getByRole("button", { name: "Back" }).click();
  for (const topic of ["World", "Business", "Science"]) {
    await expect(page.getByRole("button", { name: topic, exact: true })).toHaveAttribute("aria-pressed", "true");
  }
  await page.getByRole("button", { name: "Back" }).click();
  await expect(page.getByLabel("Paper name")).toHaveValue("The Resume Review");
});

test("Enter moves on and the words step can be skipped", async ({ page }) => {
  await signIn(page);
  await page.goto("/onboarding");
  await page.getByLabel("Paper name").press("Enter");
  await expect(page.getByRole("heading", { name: "Pick your beats" })).toBeVisible();
  for (const topic of ["World", "Business", "Science"]) await page.getByRole("button", { name: topic, exact: true }).click();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Continue", exact: true }).click(); // skip: nothing typed
  await expect(page.getByRole("heading", { name: "A quick taste test" })).toBeVisible();
});

test("onboarding is only for signed-in readers", async ({ page }) => {
  await page.goto("/onboarding");
  await expect(page).toHaveURL(/\/login\?next=%2Fonboarding$/);
});
