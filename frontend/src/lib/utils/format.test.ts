import { describe, it, expect } from "vitest";
import {
  formatDate,
  formatArea,
  formatCurrency,
  groupByArea,
  volunteersLabel,
} from "./format";

describe("formatDate", () => {
  it("returns the canonical 'Weekday, Month Day' format", () => {
    // 2025-01-15 was a Wednesday — pinning the exact string protects the
    // shape of the format from accidental regressions to short-month or
    // year-included variants. This is the format the email templates also use.
    expect(formatDate("2025-01-15")).toBe("Wednesday, January 15");
  });

  it("does not roll back a day in negative-UTC-offset zones", () => {
    // Without the noon-anchor, "2025-01-15" parsed as midnight UTC would
    // render as Jan 14 in any zone west of UTC. Catches that specific bug.
    const result = formatDate("2025-01-15");
    expect(result).toContain("January 15");
    expect(result).not.toContain("January 14");
  });

  it("handles full ISO timestamps as well as date-only strings", () => {
    // The volunteer-calls list passes `created_at` (an ISO timestamp). The
    // previous implementation appended 'T00:00:00' even to timestamps and
    // produced 'Invalid Date' — pin against that regression.
    expect(formatDate("2025-01-15T10:30:00Z")).toContain("January");
    expect(formatDate("2025-01-15T10:30:00Z")).not.toContain("Invalid");
  });

  it("returns empty string for null/undefined/blank/garbage", () => {
    expect(formatDate(null)).toBe("");
    expect(formatDate(undefined)).toBe("");
    expect(formatDate("")).toBe("");
    expect(formatDate("not-a-date")).toBe("");
  });
});

describe("formatArea", () => {
  it("converts snake_case to Title Case", () => {
    expect(formatArea("living_room")).toBe("Living Room");
    expect(formatArea("kitchen")).toBe("Kitchen");
    expect(formatArea("front_yard")).toBe("Front Yard");
  });
});

describe("formatCurrency", () => {
  it("formats as dollar amount with 2 decimal places", () => {
    expect(formatCurrency(12.5)).toBe("$12.50");
    expect(formatCurrency(0)).toBe("$0.00");
    expect(formatCurrency(1234.567)).toBe("$1234.57");
  });
});

describe("groupByArea", () => {
  it("groups items by formatted area name", () => {
    const items = [
      { area: "living_room", name: "A" },
      { area: "kitchen", name: "B" },
      { area: "living_room", name: "C" },
    ];
    const result = groupByArea(items);
    expect(Object.keys(result)).toEqual(["Living Room", "Kitchen"]);
    expect(result["Living Room"]).toHaveLength(2);
    expect(result["Kitchen"]).toHaveLength(1);
  });

  it("returns empty object for empty array", () => {
    expect(groupByArea([])).toEqual({});
  });
});

describe("volunteersLabel", () => {
  it("omits the slash when no skilled spots are needed", () => {
    expect(volunteersLabel(4, 0)).toBe("(4)");
  });
  it("includes the skilled count after a slash when > 0", () => {
    expect(volunteersLabel(4, 1)).toBe("(4/1)");
  });
});
