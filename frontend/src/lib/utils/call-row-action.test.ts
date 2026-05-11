import { describe, it, expect } from "vitest";
import type { VolunteerCallListResponse } from "$lib/api/types";
import { rowAction } from "./call-row-action";

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
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
    ...overrides,
  };
}

describe("rowAction", () => {
  it("OPEN + no tasks: hides the button entirely", () => {
    // A brand-new empty call has nothing to send — showing 'Send Call'
    // here would either error server-side or fire an empty invite. The
    // missing button is the affordance ("go add tasks first").
    expect(rowAction(call({ status: "open", task_count: 0 }))).toEqual({
      label: "",
      action: null,
    });
  });

  it("OPEN + at least one task: shows Send Call", () => {
    expect(rowAction(call({ status: "open", task_count: 3 }))).toEqual({
      label: "Send Call",
      action: "send_invites",
    });
  });

  it("WAITING shows Assign Volunteers regardless of task_count", () => {
    // task_count is irrelevant past Open — once invites have gone out the
    // call is locked in. Pinning that catches a regression that hides the
    // assign button when, say, a task got deleted post-invite.
    expect(rowAction(call({ status: "waiting", task_count: 0 }))).toEqual({
      label: "Assign Volunteers",
      action: "assign",
    });
    expect(rowAction(call({ status: "waiting", task_count: 5 }))).toEqual({
      label: "Assign Volunteers",
      action: "assign",
    });
  });

  it("ASSIGNED + no timestamp: Send Assignments", () => {
    expect(
      rowAction(
        call({ status: "assigned", task_count: 3, assignments_sent_at: null }),
      ),
    ).toEqual({ label: "Send Assignments", action: "send_assignments" });
  });

  it("ASSIGNED + timestamp set: Archive", () => {
    // The timestamp is the only signal distinguishing the two sub-states
    // of assigned. Catches a regression where assignments_sent_at is
    // ignored and the button is stuck on Send Assignments forever (which
    // would resend the same emails on every click).
    expect(
      rowAction(
        call({
          status: "assigned",
          task_count: 3,
          assignments_sent_at: "2026-05-15T10:00:00Z",
        }),
      ),
    ).toEqual({ label: "Archive", action: "archive" });
  });

  it("ARCHIVED has no button", () => {
    expect(
      rowAction(
        call({
          status: "archived",
          task_count: 5,
          assignments_sent_at: "2026-05-15T10:00:00Z",
        }),
      ),
    ).toEqual({ label: "", action: null });
  });
});
