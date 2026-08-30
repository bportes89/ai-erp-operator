import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 90000,
  globalSetup: "./global-setup.ts",
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:3001",
    headless: true,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "node start_api.mjs",
      url: "http://127.0.0.1:8001/health",
      reuseExistingServer: false,
      timeout: 120000,
      env: { ...process.env, PYTHON: process.env.PYTHON || "python" },
    },
    {
      command: "node start_web.mjs",
      url: "http://127.0.0.1:3001",
      reuseExistingServer: false,
      timeout: 120000,
    },
  ],
});