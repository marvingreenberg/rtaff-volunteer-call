import { describe, it, expect } from "vitest";
import { tasksSpanMultipleWeeks, taskWeekIndex } from "./task-weeks";

describe("tasksSpanMultipleWeeks", () => {
  it("false for a single ISO week", () => {
    // Mon 2026-05-11 .. Sat 2026-05-16 — all in the same Mon-Sun bucket.
    // Catches a regression that buckets per-day instead of per-week.
    expect(
      tasksSpanMultipleWeeks([
        { date: "2026-05-11" },
        { date: "2026-05-13" },
        { date: "2026-05-16" },
      ]),
    ).toBe(false);
  });

  it("true when tasks fall in different ISO weeks", () => {
    // Sat 5/16 + Mon 5/18 cross the Mon-Sun boundary.
    expect(
      tasksSpanMultipleWeeks([
        { date: "2026-05-16" }, // Sat (week of 5/11)
        { date: "2026-05-18" }, // Mon (week of 5/18)
      ]),
    ).toBe(true);
  });

  it("Sunday-of-week-1 is in week 1, not week 2", () => {
    // ISO weeks start Monday, so Sun 5/17 belongs with the 5/11 Monday
    // — not the next week's. Catches a regression to a Sun-start week.
    expect(
      tasksSpanMultipleWeeks([
        { date: "2026-05-11" }, // Mon
        { date: "2026-05-17" }, // Sun
      ]),
    ).toBe(false);
  });

  it("ignores tasks with no date — they don't anchor or extend the span", () => {
    // Unscheduled tasks must not silently force a "week 2" pulldown to
    // appear. Catches a regression that treats null as a distinct bucket.
    expect(
      tasksSpanMultipleWeeks([
        { date: "2026-05-13" },
        { date: null },
        { date: null },
      ]),
    ).toBe(false);
  });

  it("returns false for an empty list", () => {
    expect(tasksSpanMultipleWeeks([])).toBe(false);
  });
});

describe("taskWeekIndex", () => {
  const tasks = [
    { date: "2026-05-13" }, // week of 5/11
    { date: "2026-05-22" }, // week of 5/18
  ];

  it("returns 1 for a task in the earliest week", () => {
    expect(taskWeekIndex({ date: "2026-05-13" }, tasks)).toBe(1);
    // Boundary: any same-week date maps to 1.
    expect(taskWeekIndex({ date: "2026-05-11" }, tasks)).toBe(1);
    expect(taskWeekIndex({ date: "2026-05-17" }, tasks)).toBe(1);
  });

  it("returns 2 for a task in the following week", () => {
    expect(taskWeekIndex({ date: "2026-05-22" }, tasks)).toBe(2);
  });

  it("returns 2 for a task farther out — week 2 absorbs anything past week 1", () => {
    // A 3-week call collapses week 3 into the week-2 bucket. Pin this so a
    // future "support N-week calls" change consciously breaks the test
    // rather than silently producing a 3.
    expect(taskWeekIndex({ date: "2026-06-01" }, tasks)).toBe(2);
  });

  it("returns null when the task has no date", () => {
    expect(taskWeekIndex({ date: null }, tasks)).toBeNull();
  });
});
