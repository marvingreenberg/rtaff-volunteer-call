import { describe, it, expect } from "vitest";
import { formatMonthDay, volunteersLabel } from "./task-format";

describe("formatMonthDay", () => {
  it("formats ISO YYYY-MM-DD as MM/DD", () => {
    expect(formatMonthDay("2026-07-01")).toBe("07/01");
  });

  it("returns em-dash for null/undefined/blank", () => {
    expect(formatMonthDay(null)).toBe("—");
    expect(formatMonthDay(undefined)).toBe("—");
    expect(formatMonthDay("")).toBe("—");
  });

  it("returns em-dash for malformed input", () => {
    expect(formatMonthDay("nonsense")).toBe("—");
  });
});

describe("volunteersLabel", () => {
  it("omits skilled count when zero", () => {
    expect(volunteersLabel(4, 0)).toBe("(4)");
  });

  it("includes skilled count with slash when positive", () => {
    expect(volunteersLabel(4, 1)).toBe("(4/1)");
    expect(volunteersLabel(6, 2)).toBe("(6/2)");
  });
});
