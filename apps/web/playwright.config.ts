import { defineConfig, devices } from "@playwright/test";

const isCI = Boolean(process.env.CI);
const pythonBin = process.env.PYTHON_BIN || "python3";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  workers: isCI ? 2 : undefined,
  timeout: 30_000,
  expect: { timeout: 8_000 },
  reporter: [[isCI ? "line" : "list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:15173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  webServer: [
    {
      command: `${pythonBin} -m uvicorn app.main:app --host 127.0.0.1 --port 18182`,
      cwd: "../../backend",
      url: "http://127.0.0.1:18182/health",
      timeout: 120_000,
      reuseExistingServer: false,
    },
    {
      command:
        "VITE_API_BASE_URL=http://127.0.0.1:18182/api/v1 npm run dev -- --host 127.0.0.1 --port 15173",
      url: "http://127.0.0.1:15173",
      timeout: 120_000,
      reuseExistingServer: false,
    },
  ],
  projects: [
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile-chromium", use: { ...devices["Pixel 7"] } },
  ],
});
