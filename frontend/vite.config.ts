import { sveltekit } from "@sveltejs/kit/vite";
import { svelteTesting } from "@testing-library/svelte/vite";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [sveltekit(), svelteTesting()],
  test: {
    include: ["src/**/*.{test,spec}.{js,ts}"],
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/tests/setup.ts"],
  },
  server: {
    proxy: {
      "/api": { target: "http://localhost:8001" },
      // The warmth heartbeat (+layout.svelte) pings the backend's root
      // `/warm` endpoint. In the prod single container FastAPI serves it
      // alongside the SPA; in dev it lives on the backend, so proxy it too
      // — otherwise the ping hits Vite and 404s (still "warms," but noisy).
      "/warm": { target: "http://localhost:8001" },
    },
  },
});
