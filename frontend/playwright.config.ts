import { defineConfig, devices } from "@playwright/test";

import { E2E_ORIGIN, E2E_PORT, E2E_SERVER_ENV } from "./e2e/env";

export default defineConfig({
  testDir: "e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  reporter: process.env.CI ? "github" : "list",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: E2E_ORIGIN,
    contextOptions: { reducedMotion: "reduce" },
  },
  webServer: {
    command: `pnpm start --port ${E2E_PORT}`,
    url: E2E_ORIGIN,
    reuseExistingServer: !process.env.CI,
    env: E2E_SERVER_ENV,
  },
});
