import { describe, it, expect } from "vitest";
import type { VolunteerCallListResponse } from "$lib/api/types";
import { rowAction, lastTaskInPast } from "./call-row-action";

function call(
  overrides: Partial<VolunteerCallListResponse> = {},
): VolunteerCallListResponse {
  return {
    id: "call-1",
    title: "Test call",
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

// Stable "today" for the past-tasks tests; date math is sensitive enough
// that pinning it avoids flaky boundary failures around midnight runs.
const TODAY = new Date(2026, 4, 12); // May 12 2026

describe("rowAction", () => {
  it("OPEN + no tasks: hides the button entirely", () => {
    expect(rowAction(call({ status: "open", task_count: 0 }), TODAY)).toEqual(
      [],
    );
  });

  it("OPEN + at least one task: Send Call only", () => {
    expect(rowAction(call({ status: "open", task_count: 3 }), TODAY)).toEqual([
      { label: "Send\nCall", action: "send_invites" },
    ]);
  });

  it("WAITING: Assign Volunteers regardless of task_count", () => {
    expect(
      rowAction(call({ status: "waiting", task_count: 5 }), TODAY),
    ).toEqual([{ label: "Assign\nVolunteers", action: "assign" }]);
  });

  it("ASSIGNED + sent_at null: Update + Send Assignments", () => {
    // First-Send case. The two stacked buttons let admins jump back to
    // /assign for edits *or* push the first wave of emails.
    expect(
      rowAction(
        call({
          status: "assigned",
          task_count: 3,
          last_task_date: "2026-06-01", // future
          assignments_sent_at: null,
          assignments_changed_at: "2026-05-10T00:00:00Z",
        }),
        TODAY,
      ),
    ).toEqual([
      { label: "Update\nAssignments", action: "update_assignments" },
      { label: "Send\nAssignments", action: "send_assignments" },
    ]);
  });

  it("ASSIGNED + sent and unchanged since: only Update (no resend would be a no-op)", () => {
    // Pinning that we DON'T show a Send button when the roster matches
    // what was last sent. Otherwise a curious admin re-clicks Send and
    // gets a redundant email blast.
    expect(
      rowAction(
        call({
          status: "assigned",
          task_count: 3,
          last_task_date: "2026-06-01",
          assignments_sent_at: "2026-05-10T10:00:00Z",
          assignments_changed_at: "2026-05-10T09:00:00Z", // earlier than send
        }),
        TODAY,
      ),
    ).toEqual([{ label: "Update\nAssignments", action: "update_assignments" }]);
  });

  it("ASSIGNED + changed-after-send: Update + Send Changed Assignments", () => {
    // The defining case for this phase: admin sent once, then edited.
    // Pin the new button shape so a regression doesn't silently revert
    // to plain "Send Assignments".
    expect(
      rowAction(
        call({
          status: "assigned",
          task_count: 3,
          last_task_date: "2026-06-01",
          assignments_sent_at: "2026-05-10T09:00:00Z",
          assignments_changed_at: "2026-05-11T10:00:00Z", // after send
        }),
        TODAY,
      ),
    ).toEqual([
      { label: "Update\nAssignments", action: "update_assignments" },
      {
        label: "Send Changed\nAssignments",
        action: "send_changed_assignments",
      },
    ]);
  });

  it("ASSIGNED + last task past: ONLY Archive (overrides Update/Send)", () => {
    // The spec's "Only then." — Archive is gated on past-last-task and,
    // when shown, replaces every other action. Pin both halves: archive
    // appears AND update/send disappear.
    expect(
      rowAction(
        call({
          status: "assigned",
          last_task_date: "2026-04-30", // before TODAY = May 12
          assignments_sent_at: "2026-05-01T00:00:00Z",
          assignments_changed_at: "2026-05-02T00:00:00Z",
        }),
        TODAY,
      ),
    ).toEqual([{ label: "Archive", action: "archive" }]);
  });

  it("ARCHIVED has no buttons", () => {
    expect(rowAction(call({ status: "archived" }), TODAY)).toEqual([]);
  });
});

describe("lastTaskInPast", () => {
  it("returns false when last_task_date is null (no signal)", () => {
    // No-date call should not look 'past' — Archive must not appear on
    // a brand-new call with all-undated tasks.
    expect(lastTaskInPast({ last_task_date: null }, TODAY)).toBe(false);
  });

  it("returns false when last task is today (work might still be happening)", () => {
    // Boundary: same-day tasks aren't past yet — admin can still edit
    // assignments mid-workday without the row collapsing to Archive.
    expect(lastTaskInPast({ last_task_date: "2026-05-12" }, TODAY)).toBe(false);
  });

  it("returns true when last task is yesterday or earlier", () => {
    expect(lastTaskInPast({ last_task_date: "2026-05-11" }, TODAY)).toBe(true);
    expect(lastTaskInPast({ last_task_date: "2024-01-01" }, TODAY)).toBe(true);
  });

  it("returns false for a future task", () => {
    expect(lastTaskInPast({ last_task_date: "2026-05-13" }, TODAY)).toBe(false);
  });
});
