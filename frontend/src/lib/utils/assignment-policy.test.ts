import { describe, it, expect } from "vitest";
import {
  type PolicyTask,
  computeCounts,
  countsMessage,
  countsViolatePolicy,
  canSave,
  gateMessage,
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

describe("countsMessage", () => {
  it("reports 'fewer' when any task is under, even if others are over", () => {
    // The spec explicitly says: reporting fewer overrides reporting
    // extra. Pinning this catches a regression to a naive "first thing
    // I find" ordering.
    expect(countsMessage({ under: 1, over: 3, noLead: 0 })).toBe(
      "Some tasks have fewer than requested volunteers.",
    );
  });
  it("reports 'extra' when only over", () => {
    expect(countsMessage({ under: 0, over: 1, noLead: 0 })).toBe(
      "Some tasks have extra volunteers.",
    );
  });
  it("reports 'all requested' when neither", () => {
    expect(countsMessage({ under: 0, over: 0, noLead: 5 })).toBe(
      "All tasks have requested volunteers.",
    );
  });
});

describe("countsViolatePolicy", () => {
  it("exact: any under OR over violates", () => {
    expect(countsViolatePolicy({ under: 1, over: 0, noLead: 0 }, "exact")).toBe(
      true,
    );
    expect(countsViolatePolicy({ under: 0, over: 1, noLead: 0 }, "exact")).toBe(
      true,
    );
    expect(countsViolatePolicy({ under: 0, over: 0, noLead: 0 }, "exact")).toBe(
      false,
    );
  });
  it("over: only under violates", () => {
    // Catches a regression that conflates 'allow over' with 'allow any'.
    expect(countsViolatePolicy({ under: 1, over: 0, noLead: 0 }, "over")).toBe(
      true,
    );
    expect(countsViolatePolicy({ under: 0, over: 5, noLead: 0 }, "over")).toBe(
      false,
    );
  });
  it("over_under: nothing violates by counts", () => {
    expect(
      countsViolatePolicy({ under: 9, over: 9, noLead: 0 }, "over_under"),
    ).toBe(false);
  });
});

describe("canSave", () => {
  it("false when there are no tasks at all (Save should not enable on an empty call)", () => {
    // A new call with zero tasks would otherwise pass every other gate
    // because there's nothing to be under/over/missing-lead. Without an
    // explicit empty-tasks guard, Save would let the admin "finalize"
    // a call that has nothing to assign.
    expect(canSave([], { under: 0, over: 0, noLead: 0 }, "exact")).toBe(false);
  });
  it("true when both gates pass", () => {
    const tasks = [task({ needed: 4, assigned: 4, team_lead_id: "lead-1" })];
    expect(canSave(tasks, computeCounts(tasks), "exact")).toBe(true);
  });
  it("false when any task is missing a team lead, even if counts are fine", () => {
    const tasks = [task({ needed: 4, assigned: 4, team_lead_id: null })];
    expect(canSave(tasks, computeCounts(tasks), "over_under")).toBe(false);
  });
  it("false when counts violate, even with leads everywhere", () => {
    const tasks = [task({ needed: 4, assigned: 2, team_lead_id: "lead-1" })];
    expect(canSave(tasks, computeCounts(tasks), "exact")).toBe(false);
  });
});

describe("gateMessage", () => {
  it("team-lead failure takes precedence over counts-policy failure", () => {
    // Pin the precedence the user specified: when both gates fail, the
    // user should see the team-lead message first (it's actionable in a
    // way the policy message isn't — they have to fix something either
    // way, but the lead is concrete).
    const msg = gateMessage({ under: 1, over: 0, noLead: 2 }, "exact");
    expect(msg).toBe("Cannot close assignment: 2 tasks need a team lead");
  });
  it("subject-verb agreement: singular 'task needs' for 1, plural 'tasks need' for >1", () => {
    // Catches a regression to a naïve `${n} task${n === 1 ? '' : 's'}
    // need` rendering, which produces 'tasks need' fine but '1 task need'
    // (no 's' on the verb). The verb has to flip with the noun.
    expect(gateMessage({ under: 0, over: 0, noLead: 1 }, "exact")).toBe(
      "Cannot close assignment: 1 task needs a team lead",
    );
    expect(gateMessage({ under: 0, over: 0, noLead: 3 }, "exact")).toBe(
      "Cannot close assignment: 3 tasks need a team lead",
    );
  });
  it("falls back to the policy message when only counts violate", () => {
    expect(gateMessage({ under: 1, over: 0, noLead: 0 }, "exact")).toBe(
      'Cannot close assignment with current policy "Exact required volunteers"',
    );
    expect(gateMessage({ under: 1, over: 0, noLead: 0 }, "over")).toBe(
      'Cannot close assignment with current policy "Allow over-assignment"',
    );
  });
  it("returns an empty string when both gates pass (Message area 2 hides)", () => {
    expect(gateMessage({ under: 0, over: 0, noLead: 0 }, "exact")).toBe("");
  });
});
