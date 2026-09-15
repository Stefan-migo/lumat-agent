import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./playwright",
  testMatch: "**/*.spec.ts",
  use: {
    baseURL: "http://127.0.0.1:5173/panel/app/",
    serviceWorkers: "block",
    channel: "chrome",
    ...devices["Desktop Chrome"],
  },
  webServer: {
    command: "npm run dev -- --host 127.0.0.1",
    cwd: ".",
    url: "http://127.0.0.1:5173/panel/app/",
    reuseExistingServer: true,
  },
});
