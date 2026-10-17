import { expect, test, type Page } from "@playwright/test";

// Test accounts live in e2e/mock-api.mjs (handleAuth); none of them is real.
const RETURNING = { email: "reader@example.com", password: "correct-horse" };

const wordmark = (page: Page) => page.getByRole("link", { name: "NewsHelper home" }).first();

async function themeIs(page: Page, theme: "dark" | "light") {
  await expect(page.locator("html")).toHaveClass(theme === "dark" ? /\bdark\b/ : /^(?!.*\bdark\b).*$/);
}

test("sign-up: values survive an error, then a new reader lands in onboarding", async ({ page }) => {
  await page.goto("/signup");
  await page.getByLabel("Your name").fill("Mina Rao");
  await page.getByLabel("Email").fill("taken@example.com");
  await page.getByLabel("Password").fill("a-long-password");
  await page.getByRole("button", { name: "Start my paper" }).click();
  await expect(page.getByText(/already exists/i)).toBeVisible();
  await expect(page.getByLabel("Your name")).toHaveValue("Mina Rao");
  await expect(page.getByLabel("Password")).toHaveValue("a-long-password");

  await page.getByLabel("Email").fill("mina@example.com");
  await page.getByRole("button", { name: "Start my paper" }).click();
  await expect(page).toHaveURL(/\/onboarding$/);
  await expect(page.getByRole("heading", { name: "Name your paper" })).toBeVisible();
  await expect(page.getByText("Step 1 of 5")).toBeVisible();
  await expect(page.getByText("Shapes your paper")).toBeVisible();
});

test("sign-up: short passwords and bad emails get specific messages", async ({ page }) => {
  await page.goto("/signup");
  await page.getByLabel("Email").fill("not-an-email");
  await page.getByLabel("Password").fill("short");
  await page.getByRole("button", { name: "Start my paper" }).click();
  await expect(page.locator("#email-error")).toBeVisible();
  await expect(page.locator("#password-error")).toBeVisible();
  await expect(page.getByLabel("Email")).toHaveValue("not-an-email");
});

test("password fields can be revealed", async ({ page }) => {
  await page.goto("/login");
  const password = page.getByLabel("Password");
  await password.fill("correct-horse");
  await expect(password).toHaveAttribute("type", "password");
  await page.getByRole("button", { name: "Show characters" }).click();
  await expect(password).toHaveAttribute("type", "text");
  await page.getByRole("button", { name: "Hide characters" }).click();
  await expect(password).toHaveAttribute("type", "password");
});

test("sign-in: wrong password keeps the email, the right one opens today's paper", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(RETURNING.email);
  await page.getByLabel("Password").fill("wrong-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("That email and password don't match.")).toBeVisible();
  await expect(page.getByLabel("Email")).toHaveValue(RETURNING.email);

  await page.getByLabel("Password").fill(RETURNING.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/today$/);
  await expect(page.getByRole("heading", { name: "For You" })).toBeVisible();
});

test("one wordmark and one persistent theme from the homepage to the paper", async ({ page }) => {
  await page.goto("/");
  await expect(wordmark(page)).toBeVisible();
  await page.getByRole("button", { name: "Toggle night edition" }).click();
  await themeIs(page, "dark");

  for (const path of ["/login", "/signup"]) {
    await page.goto(path);
    await expect(wordmark(page)).toHaveText("NewsHelper.");
    await themeIs(page, "dark");
  }
  await page.reload();
  await themeIs(page, "dark");

  await page.goto("/login");
  await page.getByLabel("Email").fill(RETURNING.email);
  await page.getByLabel("Password").fill(RETURNING.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/today$/);
  await expect(wordmark(page)).toHaveText("NewsHelper.");
  await themeIs(page, "dark");
  await page.getByRole("button", { name: "Toggle night edition" }).click();
  await themeIs(page, "light");
  await page.goto("/");
  await themeIs(page, "light");
});

test("an unknown address gets the branded 404", async ({ page }) => {
  const response = await page.goto("/no-such-page");
  expect(response?.status()).toBe(404);
  await expect(page.getByRole("heading", { name: /not in today's paper/ })).toBeVisible();
  await expect(page.getByRole("link", { name: "Back to the front page" })).toHaveAttribute("href", "/");
});

test("sign-in and sign-up are reachable on every width without sideways scrolling", async ({ page }) => {
  for (const path of ["/", "/login", "/signup"]) {
    await page.goto(path);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
  await page.goto("/");
  await expect(page.getByRole("link", { name: "Sign in" }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Build my paper" }).first()).toBeVisible();
});
