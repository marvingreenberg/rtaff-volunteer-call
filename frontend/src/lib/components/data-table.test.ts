import { describe, it, expect } from "vitest";
import {
  sortItems,
  nextSortState,
  truncateText,
  type Column,
} from "./data-table";

const nameCol: Column = {
  key: "name",
  label: "Name",
  getValue: (item) => item.name as string,
};

const countCol: Column = {
  key: "count",
  label: "Count",
  getValue: (item) => item.count as number,
};

const items = [
  { name: "Charlie", count: 3 },
  { name: "alice", count: 1 },
  { name: "Bob", count: 2 },
];

describe("sortItems", () => {
  it("sorts strings case-insensitively ascending", () => {
    const sorted = sortItems(items, [nameCol], "name", "asc");
    expect(sorted.map((i) => i.name)).toEqual(["alice", "Bob", "Charlie"]);
  });

  it("sorts strings case-insensitively descending", () => {
    const sorted = sortItems(items, [nameCol], "name", "desc");
    expect(sorted.map((i) => i.name)).toEqual(["Charlie", "Bob", "alice"]);
  });

  it("sorts numbers ascending", () => {
    const sorted = sortItems(items, [countCol], "count", "asc");
    expect(sorted.map((i) => i.count)).toEqual([1, 2, 3]);
  });

  it("sorts numbers descending", () => {
    const sorted = sortItems(items, [countCol], "count", "desc");
    expect(sorted.map((i) => i.count)).toEqual([3, 2, 1]);
  });

  it("returns original array if sort key not found", () => {
    const sorted = sortItems(items, [nameCol], "missing", "asc");
    expect(sorted).toEqual(items);
  });

  it("does not mutate the original array", () => {
    const copy = [...items];
    sortItems(items, [countCol], "count", "asc");
    expect(items).toEqual(copy);
  });
});

describe("nextSortState", () => {
  it("returns ascending for a new column", () => {
    const result = nextSortState("name", "asc", "count");
    expect(result).toEqual({ key: "count", dir: "asc" });
  });

  it("returns descending when clicking same column already ascending", () => {
    const result = nextSortState("name", "asc", "name");
    expect(result).toEqual({ key: "name", dir: "desc" });
  });

  it("returns null when clicking same column already descending", () => {
    const result = nextSortState("name", "desc", "name");
    expect(result).toBeNull();
  });
});

describe("truncateText", () => {
  it("returns text unchanged when under limit", () => {
    expect(truncateText("short", 10)).toBe("short");
  });

  it("returns text unchanged when exactly at limit", () => {
    expect(truncateText("12345", 5)).toBe("12345");
  });

  it("truncates and adds ellipsis when over limit", () => {
    expect(truncateText("hello world", 5)).toBe("hello\u2026");
  });
});
