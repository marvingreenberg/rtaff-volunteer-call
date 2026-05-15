import { defineConfig } from "@playwright/test";

// The Playwright config is tuned for the demo recording, not headless CI.
// It assumes `make dev` is already running (frontend on 5173, backend on
// 8001, Mailpit on 8025). DEMO_MODE is deliberately *not* enabled so
// magic-link emails actually land in Mailpit and the demo can show them
// arriving.

export default defineConfig({
  testDir: "e2e",
  timeout: 180_000,
  retries: 0,
  reporter: "list",
  outputDir: "test-results/demo",
  use: {
    baseURL: process.env.BASE_URL || "http://localhost:5173",
    headless: false,
    // Sized to fit comfortably on a 1440-wide laptop screen with room for
    // the macOS menu bar and Chrome chrome. The recorded video uses the
    // viewport size, not the window size, so video stays 1280x800.
    viewport: { width: 1280, height: 800 },
    video: "on",
    screenshot: "only-on-failure",
    launchOptions: {
      slowMo: 180,
      args: ["--window-size=1280,860", "--window-position=40,40"],
    },
  },
});
