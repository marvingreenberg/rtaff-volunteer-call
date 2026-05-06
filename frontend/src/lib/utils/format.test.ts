import { describe, it, expect } from "vitest";
import {
  formatDate,
  formatDateFull,
  formatDateShort,
  formatArea,
  formatCurrency,
  groupByArea,
} from "./format";

describe("formatDate", () => {
  it("formats date in short US format", () => {
    const result = formatDate("2025-01-15");
    expect(result).toContain("Jan");
    expect(result).toContain("15");
    expect(result).toContain("2025");
  });
});

describe("formatDateFull", () => {
  it("includes weekday", () => {
    const result = formatDateFull("2025-01-15");
    expect(result).toContain("Wed");
    expect(result).toContain("Jan");
    expect(result).toContain("15");
  });
});

describe("formatDateShort", () => {
  it("formats without year", () => {
    const result = formatDateShort("2025-01-15");
    expect(result).toContain("Jan");
    expect(result).toContain("15");
    expect(result).not.toContain("2025");
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
