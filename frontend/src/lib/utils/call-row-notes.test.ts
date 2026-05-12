import { describe, it, expect } from "vitest";
import type { VolunteerCallListResponse } from "$lib/api/types";
import { rowNotes } from "./call-row-notes";

function call(
  overrides: Partial<VolunteerCallListResponse> = {},
): VolunteerCallListResponse {
  return {
    id: "c1",
    title: "t",
    program: "RTX",
    status: "open",
    task_count: 0,
    assignments_sent_at: null,
    assignments_changed_at: null,
    volunteers_responded: 0,
    spots_filled: 0,
    spots_needed: 0,
    tasks_fully_assigned: 0,
    last_task_date: null,
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
    ...overrides,
  };
}

describe("rowNotes", () => {
  it("OPEN: empty (no notes until invites go out)", () => {
    expect(rowNotes(call({ status: "open", task_count: 3 }))).toBe("");
  });

  it("WAITING: pluralizes correctly for 0 / 1 / N volunteers responded", () => {
    // Catches the 's' pluralization regression on the boundary.
    expect(rowNotes(call({ status: "waiting", volunteers_responded: 0 }))).toBe(
      "0 volunteers responded",
    );
    expect(rowNotes(call({ status: "waiting", volunteers_responded: 1 }))).toBe(
      "1 volunteer responded",
    );
    expect(rowNotes(call({ status: "waiting", volunteers_responded: 5 }))).toBe(
      "5 volunteers responded",
    );
  });

  it("ASSIGNED: shows spots-filled and tasks-fully-assigned with the · separator", () => {
    // Pin the exact format because mockup + summary on /assign use this
    // same shape; any drift will read as inconsistent to admins.
    expect(
      rowNotes(
        call({
          status: "assigned",
          spots_filled: 8,
          spots_needed: 12,
          tasks_fully_assigned: 2,
          task_count: 5,
        }),
      ),
    ).toBe("8/12 spots filled · 2/5 tasks fully assigned");
  });

  it("ASSIGNED: handles a fresh-from-Done-Assigning state (zeros)", () => {
    // 0/12, 0/5 — same as the user's mockup. Should render cleanly,
    // not "0/0 spots filled" or NaN.
    expect(
      rowNotes(
        call({
          status: "assigned",
          spots_filled: 0,
          spots_needed: 12,
          tasks_fully_assigned: 0,
          task_count: 5,
        }),
      ),
    ).toBe("0/12 spots filled · 0/5 tasks fully assigned");
  });

  it("ARCHIVED: empty (the work is done; no live stats)", () => {
    expect(rowNotes(call({ status: "archived" }))).toBe("");
  });
});
