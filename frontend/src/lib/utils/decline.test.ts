import { describe, it, expect } from "vitest";
import type {
  MyAssignment,
  TaskConflicts,
  VolunteerCallListResponse,
} from "$lib/api/client";
import {
  declineMessagePrefill,
  assignedCallIds,
  callsAwaitingResponse,
  conflictFor,
} from "./decline";

function call(id: string): VolunteerCallListResponse {
  return {
    id,
    title: id,
    program: "RTX",
    status: "waiting",
    task_count: 1,
    created_at: "2026-06-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
  } as VolunteerCallListResponse;
}

function assignment(callId: string, taskId: string): MyAssignment {
  return {
    assignment_id: `a-${taskId}`,
    task_id: taskId,
    team_lead_name: null,
    task_description: "x",
    address: null,
    city: null,
    date: null,
    time_start: null,
    time_end: null,
    role: "volunteer",
    confirmed: false,
    call_title: "x",
    call_id: callId,
  };
}

describe("declineMessagePrefill", () => {
  it("addresses the team lead by name when known", () => {
    // Pins the exact wording the volunteer sees pre-filled; a regression that
    // drops the lead's name or the date would surface here.
    expect(declineMessagePrefill("Bard Jackson", "Monday, June 1")).toBe(
      "Sorry Bard Jackson, I'm unable to come to the project on Monday, June 1.",
    );
  });

  it("omits the name when there is no team lead", () => {
    expect(declineMessagePrefill(null, "Monday, June 1")).toBe(
      "Sorry, I'm unable to come to the project on Monday, June 1.",
    );
  });
});

describe("callsAwaitingResponse", () => {
  it("hides calls the volunteer is already assigned to", () => {
    // The grid is only for not-yet-assigned people; an assigned call must drop
    // out of the grid list (it's shown in the assignments view instead).
    const calls = [call("c1"), call("c2")];
    const result = callsAwaitingResponse(calls, [assignment("c2", "t9")]);
    expect(result.map((c) => c.id)).toEqual(["c1"]);
  });

  it("keeps all calls when the volunteer has no assignments", () => {
    const calls = [call("c1"), call("c2")];
    expect(callsAwaitingResponse(calls, []).map((c) => c.id)).toEqual([
      "c1",
      "c2",
    ]);
  });
});

describe("assignedCallIds", () => {
  it("collects the distinct call ids from assignments", () => {
    const ids = assignedCallIds([
      assignment("c1", "t1"),
      assignment("c1", "t2"),
    ]);
    expect([...ids]).toEqual(["c1"]);
  });
});

describe("conflictFor", () => {
  const conflicts: Record<string, Record<string, TaskConflicts>> = {
    c1: {
      t1: { task_id: "t1", has_conflict: true, conflicts: [] },
      t2: { task_id: "t2", has_conflict: false, conflicts: [] },
    },
  };

  it("returns the conflict only when has_conflict is true", () => {
    expect(conflictFor(conflicts, "c1", "t1")?.task_id).toBe("t1");
  });

  it("returns null when the task has no conflict", () => {
    expect(conflictFor(conflicts, "c1", "t2")).toBeNull();
  });

  it("returns null when nothing is loaded for the call/task", () => {
    expect(conflictFor(conflicts, "c1", "nope")).toBeNull();
    expect(conflictFor(conflicts, "other", "t1")).toBeNull();
  });
});
