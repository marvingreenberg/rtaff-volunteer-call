import { defineConfig } from "@playwright/test";

// Two modes share this config:
//   - Recording / manual walkthrough (`make demo`): headed, slow-mo, video
//     on, generous display holds — tuned to look good on camera.
//   - Headless smoke (`make test-e2e`, AUTODEMO=1): the same demo path run
//     as a fast CI check. The on-camera niceties (slow-mo, video, the long
//     display holds in demo.spec.ts) only add wall-clock time here — and at
//     full recording speed the walkthrough overruns the 20-minute test
//     budget and the video-encode hangs teardown. So in smoke mode we run
//     headless, drop slow-mo, and skip video. The display holds are scaled
//     down in demo.spec.ts off the same AUTODEMO flag.
//
// Both assume `make dev` is already running (frontend 5173, backend 8001,
// Mailpit 8025). DEMO_MODE is deliberately *not* enabled so magic-link
// emails actually land in Mailpit.
const SMOKE = process.env.AUTODEMO === "1";

export default defineConfig({
  testDir: "e2e",
  timeout: 180_000,
  retries: 0,
  reporter: "list",
  outputDir: "test-results/demo",
  use: {
    baseURL: process.env.BASE_URL || "http://localhost:5173",
    headless: SMOKE,
    // Sized to fit comfortably on a 1440-wide laptop screen with room for
    // the macOS menu bar and Chrome chrome. The recorded video uses the
    // viewport size, not the window size, so video stays 1280x800.
    viewport: { width: 1280, height: 800 },
    // Video is for the recording; skip it in smoke mode (encoding a long
    // run is what hangs teardown).
    video: SMOKE ? "off" : "on",
    screenshot: "only-on-failure",
    launchOptions: {
      slowMo: SMOKE ? 0 : 180,
      args: ["--window-size=1280,860", "--window-position=40,40"],
    },
  },
});
