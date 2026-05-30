import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  assignmentFlash,
  setAssignmentFlash,
  dismissAssignmentFlash,
} from "./flash.svelte";

beforeEach(() => {
  vi.useFakeTimers();
  dismissAssignmentFlash();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("assignment flash store", () => {
  it("stores a trimmed message", () => {
    // Trimming matters: the assign page joins issue lines and may pass a
    // string with trailing space when only one issue applies. A spurious
    // banner-with-whitespace would still render the {#if}.
    setAssignmentFlash("  ‼️ 3/7 tasks have no team lead  ");
    expect(assignmentFlash.message).toBe("‼️ 3/7 tasks have no team lead");
  });

  it("treats an empty/whitespace message as a clear (no banner)", () => {
    setAssignmentFlash("something");
    setAssignmentFlash("   ");
    // Catches showing a blank warning banner when there were no issues.
    expect(assignmentFlash.message).toBe("");
  });

  it("auto-clears after the 10s TTL", () => {
    setAssignmentFlash("heads up");
    expect(assignmentFlash.message).toBe("heads up");
    vi.advanceTimersByTime(9_999);
    expect(assignmentFlash.message).toBe("heads up");
    vi.advanceTimersByTime(1);
    // Catches a missing/over-long timer that would pin the banner forever.
    expect(assignmentFlash.message).toBe("");
  });

  it("resets the TTL when a newer message replaces an older one", () => {
    setAssignmentFlash("first");
    vi.advanceTimersByTime(8_000);
    setAssignmentFlash("second");
    // 8s after the first, 0s after the second — must still be showing.
    vi.advanceTimersByTime(8_000);
    expect(assignmentFlash.message).toBe("second");
    // ...and clear 10s after the *second* was set.
    vi.advanceTimersByTime(2_000);
    expect(assignmentFlash.message).toBe("");
  });

  it("dismiss clears immediately and cancels the timer", () => {
    setAssignmentFlash("dismiss me");
    dismissAssignmentFlash();
    expect(assignmentFlash.message).toBe("");
    // Advancing past the TTL must not resurrect or error.
    vi.advanceTimersByTime(20_000);
    expect(assignmentFlash.message).toBe("");
  });
});
