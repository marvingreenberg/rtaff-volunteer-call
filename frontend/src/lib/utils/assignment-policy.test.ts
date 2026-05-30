import { describe, it, expect } from "vitest";
import {
  type PolicyTask,
  computeCounts,
  assignmentIssues,
} from "./assignment-policy";

function task(partial: {
  needed: number;
  assigned: number;
  team_lead_id?: string | null;
}): PolicyTask {
  return {
    volunteers_needed: partial.needed,
    assignments: Array.from({ length: partial.assigned }, (_, i) => ({
      assignment_id: `a-${i}`,
    })),
    // Use `in` so passing an explicit `null` is honored — `partial.team_lead_id ?? "lead-1"`
    // would silently coerce null back to the default.
    team_lead_id:
      "team_lead_id" in partial ? (partial.team_lead_id ?? null) : "lead-1",
  };
}

describe("computeCounts", () => {
  it("counts under, over, and tasks missing a team lead", () => {
    // Mix of states is the most likely real input. Pinning that under/
    // over/noLead are independent counters (a single task can be both
    // under *and* missing a lead) catches an aggregation bug where one
    // dimension silently masks another.
    const tasks: PolicyTask[] = [
      task({ needed: 4, assigned: 2, team_lead_id: "lead-1" }), // under
      task({ needed: 4, assigned: 5, team_lead_id: "lead-2" }), // over
      task({ needed: 4, assigned: 4, team_lead_id: null }), // exact, no lead
      task({ needed: 4, assigned: 2, team_lead_id: null }), // under AND no lead
    ];
    expect(computeCounts(tasks)).toEqual({ under: 2, over: 1, noLead: 2 });
  });

  it("returns zeros for an empty task list", () => {
    expect(computeCounts([])).toEqual({ under: 0, over: 0, noLead: 0 });
  });
});

describe("assignmentIssues", () => {
  it("reports the team-lead line as 'noLead/total' with the ‼️ icon", () => {
    // Catches a regression to the wrong denominator (e.g. noLead/noLead)
    // or dropping the count — the coordinator needs "3 of 7", not "3".
    expect(assignmentIssues({ under: 0, over: 0, noLead: 3 }, 7)).toEqual([
      "‼️ 3/7 tasks have no team lead",
    ]);
  });

  it("reports the counts line for under-filled tasks", () => {
    expect(assignmentIssues({ under: 2, over: 0, noLead: 0 }, 5)).toEqual([
      "⚠️ not all tasks have desired volunteers",
    ]);
  });

  it("reports the counts line for over-filled tasks too", () => {
    // Over-fill is still "not desired" — catches a regression that only
    // warns on under and silently accepts extras.
    expect(assignmentIssues({ under: 0, over: 1, noLead: 0 }, 5)).toEqual([
      "⚠️ not all tasks have desired volunteers",
    ]);
  });

  it("lists the team-lead line first, then counts, when both apply", () => {
    // Order matters: the popup shows these as two lines and the banner
    // joins them — team-lead is the higher-priority, more concrete fix.
    expect(assignmentIssues({ under: 1, over: 0, noLead: 2 }, 4)).toEqual([
      "‼️ 2/4 tasks have no team lead",
      "⚠️ not all tasks have desired volunteers",
    ]);
  });

  it("returns an empty array when everything is staffed", () => {
    // Drives the 'no warning' path — a non-empty array here would pop a
    // spurious confirmation at Send and a banner with nothing to say.
    expect(assignmentIssues({ under: 0, over: 0, noLead: 0 }, 6)).toEqual([]);
  });
});
