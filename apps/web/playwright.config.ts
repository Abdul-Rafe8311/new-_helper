import { defineConfig, devices } from "@playwright/test";

const PORT = Number(process.env.E2E_PORT ?? 3100);
const MOCK_API_PORT = Number(process.env.MOCK_API_PORT ?? 3199);
const MOCK_API_URL = `http://127.0.0.1:${MOCK_API_PORT}`;

/**
 * E2E tests against the production build (`pnpm build:e2e` first), which proxies /api/* to an
 * in-memory mock API (e2e/mock-api.mjs). The mock is started here alongside the web server.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: [
    {
      command: "node e2e/mock-api.mjs",
      env: { MOCK_API_PORT: String(MOCK_API_PORT) },
      url: `${MOCK_API_URL}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 15_000,
    },
    {
      command: `pnpm start -p ${PORT}`,
      env: { API_URL: MOCK_API_URL },
      url: `http://127.0.0.1:${PORT}`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
