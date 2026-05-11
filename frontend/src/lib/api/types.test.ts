import { describe, it, expect } from "vitest";
import { suggestCallTitle } from "./types";

describe("suggestCallTitle", () => {
  it("returns the fixed phrase for the single-task programs", () => {
    // Catches a regression where the per-program label table drifts from
    // what RT-AFF actually calls these calls in conversation.
    expect(suggestCallTitle("ACR")).toBe("AC Rescue call");
    expect(suggestCallTitle("RAMP")).toBe("Ramp Install call");
    expect(suggestCallTitle("LIFT")).toBe("Chairlift call");
  });

  it("RTX anchors to next-Monday + 11 days (2nd Friday) when today is mid-week", () => {
    // Wednesday 2026-05-13 → next Monday 5/18, +11 days = Friday 5/29.
    // Both fall in May, so the end month name is omitted ("May 18 - 29").
    // Pinning the exact string catches off-by-one bugs in the +11 math
    // and the same-month-omission rule.
    expect(suggestCallTitle("RTX", new Date(2026, 4, 13))).toBe(
      "RTX Call May 18 - 29",
    );
  });

  it("RTX treats today-is-Monday as the start (no skip to next week)", () => {
    // Monday 2026-05-11 → Monday is today; +11 days = Friday 5/22.
    // Catches the "off by 7 days" bug where today-is-Monday silently
    // bumps the cycle forward a week.
    expect(suggestCallTitle("RTX", new Date(2026, 4, 11))).toBe(
      "RTX Call May 11 - 22",
    );
  });

  it("RTX from a Sunday picks the *next* Monday (not the prior one)", () => {
    // Sunday 2026-05-10 → next Monday 5/11; +11 = Friday 5/22.
    // Catches the dow=0 edge: a naive (1 - dow) formula would resolve to
    // Monday of the *previous* week (5/4).
    expect(suggestCallTitle("RTX", new Date(2026, 4, 10))).toBe(
      "RTX Call May 11 - 22",
    );
  });

  it("RTX keeps both month names when the cycle crosses a month boundary", () => {
    // Wednesday 2026-04-22 → Monday 4/27; +11 = Friday 5/8.
    // Different months, so the closing date keeps its month name to stay
    // unambiguous. Catches a regression where same-month-omission also
    // strips the cross-month case.
    expect(suggestCallTitle("RTX", new Date(2026, 3, 22))).toBe(
      "RTX Call April 27 - May 8",
    );
  });
});
