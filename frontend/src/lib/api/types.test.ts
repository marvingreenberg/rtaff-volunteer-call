import { describe, it, expect } from "vitest";
import { suggestCallTitle } from "./types";

describe("suggestCallTitle", () => {
  it("returns the fixed phrase for the single-task programs", () => {
    // Catches a regression where the per-program label table drifts from
    // what RT-AFF actually calls these calls in conversation.
    expect(suggestCallTitle("ACR", null)).toBe("AC Rescue call");
    expect(suggestCallTitle("RAMP", null)).toBe("Ramp Install call");
    expect(suggestCallTitle("LIFT", null)).toBe("Chairlift call");
  });

  it("returns empty for RTX with no task date yet", () => {
    // The form depends on this returning empty so it doesn't show a half-
    // baked title (e.g. "Rebuilding Together /-/") before the user picks a
    // date.
    expect(suggestCallTitle("RTX", null)).toBe("");
    expect(suggestCallTitle("RTX", "")).toBe("");
    expect(suggestCallTitle("RTX", "not-a-date")).toBe("");
  });

  it("RTX wraps the task date into the Mon-Sun span containing it", () => {
    // 2026-05-13 is a Wednesday — the containing Mon..Sun is 5/11..5/17.
    // Pinning the exact string protects the date arithmetic from off-by-
    // one bugs (Sunday-anchored vs Monday-anchored, or a TZ rollback that
    // would silently produce the prior week).
    expect(suggestCallTitle("RTX", "2026-05-13")).toBe(
      "Rebuilding Together 5/11-5/17",
    );
    // Boundary: a Monday should map to the same week (not the previous one).
    expect(suggestCallTitle("RTX", "2026-05-11")).toBe(
      "Rebuilding Together 5/11-5/17",
    );
    // Boundary: a Sunday should map to the week starting the previous
    // Monday (Sun-rollover bug catcher: 2026-05-17 is a Sunday).
    expect(suggestCallTitle("RTX", "2026-05-17")).toBe(
      "Rebuilding Together 5/11-5/17",
    );
  });

  it("RTX month roll-over still produces the correct Mon-Sun pair", () => {
    // 2026-04-30 is a Thursday; week is 4/27..5/3 (crosses month boundary).
    expect(suggestCallTitle("RTX", "2026-04-30")).toBe(
      "Rebuilding Together 4/27-5/3",
    );
  });
});
