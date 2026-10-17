import { expect, test, type Page } from "@playwright/test";

const MOCK_API = `http://127.0.0.1:${process.env.MOCK_API_PORT ?? 3199}`;
const SHOTS = process.env.QUIZ_SHOTS;

let counter = 0;

type LoggedEvent = { type: string; value?: number; meta?: { q?: number; kind?: string } };

async function signIn(page: Page, seed: { quiz?: "on" | "none" } = {}): Promise<string> {
  const id = `quiz-reader-${process.pid}-${Date.now()}-${counter++}`;
  await page.context().addCookies([{ name: "dp_session", value: id, domain: "127.0.0.1", path: "/" }]);
  const response = await page.request.post(`${MOCK_API}/__seed`, {
    headers: { Cookie: `dp_session=${id}`, "Content-Type": "application/json" },
    data: seed,
  });
  expect(response.ok()).toBe(true);
  return id;
}

async function quizEvents(page: Page, id: string): Promise<LoggedEvent[]> {
  const response = await page.request.get(`${MOCK_API}/__state`, { headers: { Cookie: `dp_session=${id}` } });
  const state = (await response.json()) as { events: LoggedEvent[] };
  return state.events.filter((e) => e.type === "quiz_answer");
}

/** Server-rendered markup exists before React attaches; wait until it has, or early clicks are lost. */
const hydrated = (page: Page) =>
  page.waitForFunction(() =>
    Object.keys(document.querySelector("[data-story]") ?? {}).some((key) => key.startsWith("__reactFiber")),
  );

const VIEWPORTS = [
  { name: "1440px", width: 1440, height: 900 },
  { name: "390px", width: 390, height: 844 },
];

for (const viewport of VIEWPORTS) {
  test(`answer the three questions and the streak shows 1 (${viewport.name})`, async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop", "viewports are set explicitly below");
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    const id = await signIn(page);
    await page.goto("/today");
    await hydrated(page);

    // the new masthead button must not push the page sideways
    if (SHOTS) await page.screenshot({ path: `${SHOTS}/top-${viewport.name}.png` });
    const [scroll, inner] = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
    expect(scroll).toBeLessThanOrEqual(inner);
    // ...and the account menu is still on screen
    const avatar = await page.getByRole("button", { name: /account|menu for|rafe/i }).last().boundingBox();
    expect(avatar && avatar.x + avatar.width).toBeLessThanOrEqual(inner - 8);

    const quiz = page.getByTestId("quiz");
    await quiz.scrollIntoViewIfNeeded();
    await expect(quiz.getByRole("heading", { name: "Can you name three things you learned?" })).toBeVisible();
    await expect(page.getByTestId("quiz-streak-count")).toHaveText("0");
    const questions = quiz.getByTestId("quiz-question");
    await expect(questions).toHaveCount(3);

    // right, wrong, right
    await questions.nth(0).getByRole("button", { name: /AI agents/ }).click();
    await expect(questions.nth(0).getByTestId("quiz-feedback")).toContainText("Correct.");
    await expect(questions.nth(0).getByTestId("quiz-feedback")).toContainText("negotiating their own contracts");
    await questions.nth(1).getByRole("button", { name: /Rizwan/ }).click();
    await expect(questions.nth(1).getByTestId("quiz-feedback")).toContainText("Not quite.");
    await expect(questions.nth(1).getByTestId("quiz-feedback")).toContainText("Babar found his rhythm");
    await expect(page.getByTestId("quiz-streak-count")).toHaveText("0"); // not finished yet
    await questions.nth(2).getByRole("button", { name: /synchronised pause/ }).click();
    await expect(questions.nth(2).getByTestId("quiz-feedback")).toContainText("Correct.");

    await expect(page.getByTestId("quiz-streak")).toHaveText("Streak: 1 day");
    await expect(quiz).toContainText("You got 2 of 3.");
    // the options are real buttons, and the verdict sits in a live region
    await expect(questions.nth(0).getByTestId("quiz-feedback")).toHaveAttribute("aria-live", "polite");
    if (SHOTS) await quiz.screenshot({ path: `${SHOTS}/quiz-${viewport.name}.png` });

    await expect
      .poll(async () => (await quizEvents(page, id)).map((e) => [e.value, e.meta?.q, e.meta?.kind]))
      .toEqual([
        [1, 0, "quiz"],
        [0, 1, "quiz"],
        [1, 2, "quiz"],
      ]);

    // a reload keeps the server's streak
    await page.reload();
    await hydrated(page);
    await expect(page.getByTestId("quiz-streak")).toHaveText("Streak: 1 day");
  });
}

test("Still remember? asks one question from yesterday's paper and logs it as a recall answer", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop");
  const id = await signIn(page);
  await page.goto("/today");
  await hydrated(page);
  const recall = page.getByTestId("recall");
  await expect(recall).toBeVisible();
  await expect(recall.getByRole("heading", { name: /Still remember/ })).toBeVisible();
  const options = recall.getByRole("button");
  expect(await options.count()).toBeGreaterThanOrEqual(3);
  await options.first().click();
  await expect(recall.getByTestId("quiz-feedback")).not.toBeEmpty();
  await expect.poll(async () => (await quizEvents(page, id)).map((e) => e.meta?.kind)).toEqual(["recall"]);
  // a recall answer is not a finished quiz
  await expect(page.getByTestId("quiz-streak-count")).toHaveText("0");
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/recall-top.png` });
});

test("an edition without quiz questions shows no quiz and no recall card", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop");
  await signIn(page, { quiz: "none" });
  await page.goto("/today");
  await hydrated(page);
  await expect(page.getByTestId("quiz")).toHaveCount(0);
  await expect(page.getByTestId("recall")).toHaveCount(0);
  await expect(page.getByText("Can you name three things you learned?")).toHaveCount(0);
});

test("the masthead has a disabled Listen placeholder", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop");
  await signIn(page);
  await page.goto("/today");
  const listen = page.getByRole("button", { name: "Listen (coming soon)" });
  await expect(listen).toBeVisible();
  await expect(listen).toBeDisabled();
});
