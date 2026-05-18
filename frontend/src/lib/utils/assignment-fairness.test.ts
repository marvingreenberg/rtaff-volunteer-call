/**
 * Bugs each test catches:
 *
 * - sort_assignments_this_call: regression where the comparator sorts by
 *   name first, so a heavily-assigned volunteer stays at the top of the
 *   list and gets picked again for the next task.
 * - sort_last_date_nulls_first: regression where null last_assignment_date
 *   is treated as "today" (or sorted last), pushing brand-new volunteers
 *   to the bottom instead of the top.
 * - badges_fully_booked_at_cap: regression where 💯 fails to fire at exact
 *   per-week cap equality — the entire intent of the badge ("you said max 2
 *   and you have 2 in week 1").
 * - badges_exhausted_only_when_over: regression where 🥵 fires at exact cap
 *   equality, conflating "fully booked" with "oversubscribed". 🥵 must
 *   require count > cap; the equality case belongs to 💯.
 * - quartile_includes_ties_at_cutoff: regression where the cutoff index
 *   alone bounds the 😴 set, so ties at the boundary get split arbitrarily
 *   — two volunteers with the same idle date land on opposite sides.
 * - conflict_filter_hides_same_date_assigned: regression where a
 *   volunteer assigned to another task on the same date stays clickable
 *   in the Available list, allowing silent double-booking.
 */

import { describe, it, expect } from "vitest";
import {
  buildFairnessContext,
  fairnessCompare,
  badgesFor,
  partitionAvailable,
  computeIdleQuartile,
  spreadsheetConflictKeys,
} from "./assignment-fairness";
import type {
  AvailableVolunteer,
  TaskAssignment,
  TaskOverviewItem,
  VolunteerOverviewItem,
} from "$lib/api/types";

function vol(
  partial: Partial<VolunteerOverviewItem> & {
    id: string;
    first?: string;
  },
): VolunteerOverviewItem {
  return {
    person_id: partial.id,
    person_name: `${partial.first ?? partial.id} Last`,
    first_name: partial.first ?? partial.id,
    last_name: "Last",
    initials: (partial.first ?? partial.id).slice(0, 2),
    skills: partial.skills ?? [],
    phone: null,
    available_task_ids: partial.available_task_ids ?? [],
    max_tasks_per_week: partial.max_tasks_per_week ?? 2,
    max_tasks_per_week_2: partial.max_tasks_per_week_2 ?? 2,
    assignments_this_call: partial.assignments_this_call ?? 0,
    last_assignment_date: partial.last_assignment_date ?? null,
    assignments_trailing_3mo: partial.assignments_trailing_3mo ?? 0,
  };
}

function avail(id: string, first = id): AvailableVolunteer {
  return {
    person_id: id,
    person_name: `${first} Last`,
    first_name: first,
    last_name: "Last",
    initials: first.slice(0, 2),
    skills: [],
  };
}

function task(partial: {
  id: string;
  date?: string | null;
  skilled_needed?: number;
  assignments?: TaskAssignment[];
  available?: AvailableVolunteer[];
}): TaskOverviewItem {
  return {
    task_id: partial.id,
    short_description: `Task ${partial.id}`,
    city: null,
    date: partial.date ?? null,
    time_start: null,
    time_end: null,
    volunteers_needed: 4,
    skilled_needed: partial.skilled_needed ?? 0,
    status: "open",
    notes: null,
    team_lead_id: null,
    team_lead_name: null,
    assignments: partial.assignments ?? [],
    available_volunteers: partial.available ?? [],
  };
}

function assignmentRow(personId: string, first: string): TaskAssignment {
  return {
    assignment_id: `a-${personId}`,
    person_id: personId,
    person_name: `${first} Last`,
    first_name: first,
    last_name: "Last",
    initials: first.slice(0, 2),
    skills: [],
    role: "volunteer",
  };
}

describe("fairnessCompare", () => {
  it("sorts by assignments_this_call before name (sort_assignments_this_call)", () => {
    const ctx = buildFairnessContext(
      [
        vol({ id: "alex", first: "Alex", assignments_this_call: 3 }),
        vol({ id: "bryan", first: "Bryan", assignments_this_call: 0 }),
      ],
      [],
    );
    const sorted = [avail("alex", "Alex"), avail("bryan", "Bryan")].sort(
      (a, b) => fairnessCompare(a, b, ctx),
    );
    expect(sorted.map((v) => v.person_id)).toEqual(["bryan", "alex"]);
  });

  it("nulls sort first on last_assignment_date (sort_last_date_nulls_first)", () => {
    const ctx = buildFairnessContext(
      [
        vol({ id: "old", last_assignment_date: "2020-01-01" }),
        vol({ id: "new", last_assignment_date: null }), // brand new
      ],
      [],
    );
    const sorted = [avail("old"), avail("new")].sort((a, b) =>
      fairnessCompare(a, b, ctx),
    );
    expect(sorted.map((v) => v.person_id)).toEqual(["new", "old"]);
  });

  it("breaks ties by trailing_3mo then first name", () => {
    const ctx = buildFairnessContext(
      [
        vol({
          id: "x",
          first: "Xen",
          assignments_trailing_3mo: 5,
        }),
        vol({
          id: "y",
          first: "Yara",
          assignments_trailing_3mo: 2,
        }),
        vol({
          id: "z",
          first: "Anne",
          assignments_trailing_3mo: 5,
        }),
      ],
      [],
    );
    const sorted = [avail("x"), avail("y"), avail("z")].sort((a, b) =>
      fairnessCompare(a, b, ctx),
    );
    // y has lowest 3mo, then z (Anne, 5), then x (Xen, 5).
    expect(sorted.map((v) => v.person_id)).toEqual(["y", "z", "x"]);
  });
});

describe("badgesFor", () => {
  // Build a per-week assignment scenario: two week-1 tasks with `personId`
  // assigned to both. Used by the per-week badge tests.
  const week1Tasks = (personId: string, dates: string[]): TaskOverviewItem[] =>
    dates.map((d, i) =>
      task({
        id: `t${i}`,
        date: d,
        assignments: [assignmentRow(personId, personId)],
      }),
    );

  it("fires fullyBooked (💯) at exact per-week cap equality (badges_fully_booked_at_cap)", () => {
    // 2 assignments in week 1, cap 2 → fullyBooked for week 1, not exhausted.
    const tasks = week1Tasks("tina", ["2025-12-01", "2025-12-03"]);
    const ctx = buildFairnessContext(
      [vol({ id: "tina", max_tasks_per_week: 2 })],
      tasks,
    );
    const b = badgesFor("tina", tasks[0], ctx);
    expect(b.fullyBookedWeeks).toEqual([1]);
    expect(b.fullyBookedReason).toBe("2/2 for week 1");
    expect(b.exhausted).toBe(false);
  });

  it("only fires exhausted (🥵) when over cap, not at equality (badges_exhausted_only_when_over)", () => {
    // 3 assignments in week 1, cap 2 → exhausted (over), NOT fullyBooked.
    const tasks = week1Tasks("over", [
      "2025-12-01",
      "2025-12-02",
      "2025-12-03",
    ]);
    const ctx = buildFairnessContext(
      [vol({ id: "over", max_tasks_per_week: 2 })],
      tasks,
    );
    const b = badgesFor("over", tasks[0], ctx);
    expect(b.exhausted).toBe(true);
    expect(b.exhaustedReason).toContain("3 of max 2 for week 1");
    expect(b.fullyBookedWeeks).toEqual([]);
  });

  it("does not fire either badge under cap", () => {
    const tasks = week1Tasks("light", ["2025-12-01"]);
    const ctx = buildFairnessContext(
      [vol({ id: "light", max_tasks_per_week: 2 })],
      tasks,
    );
    const b = badgesFor("light", tasks[0], ctx);
    expect(b.exhausted).toBe(false);
    expect(b.fullyBookedWeeks).toEqual([]);
  });

  it("tracks week 1 and week 2 independently with separate caps", () => {
    // Week 1 cap = 1 (full), week 2 cap = 4 (half). Tasks: 1 in week 1
    // (2025-12-01 Mon), 2 in week 2 (2025-12-08, 2025-12-10).
    const tasks: TaskOverviewItem[] = [
      task({
        id: "w1a",
        date: "2025-12-01",
        assignments: [assignmentRow("mix", "Mix")],
      }),
      task({
        id: "w2a",
        date: "2025-12-08",
        assignments: [assignmentRow("mix", "Mix")],
      }),
      task({
        id: "w2b",
        date: "2025-12-10",
        assignments: [assignmentRow("mix", "Mix")],
      }),
    ];
    const ctx = buildFairnessContext(
      [vol({ id: "mix", max_tasks_per_week: 1, max_tasks_per_week_2: 4 })],
      tasks,
    );
    const b = badgesFor("mix", tasks[0], ctx);
    expect(b.fullyBookedWeeks).toEqual([1]);
    expect(b.fullyBookedReason).toBe("1/1 for week 1");
    expect(b.exhausted).toBe(false);
  });

  it("skilled badge fires when task needs skilled volunteers AND volunteer has any skill", () => {
    const ctx = buildFairnessContext(
      [vol({ id: "handy", skills: ["plumbing"] as never })],
      [],
    );
    expect(
      badgesFor("handy", task({ id: "t1", skilled_needed: 1 }), ctx).skilled,
    ).toBe(true);
    expect(
      badgesFor("handy", task({ id: "t1", skilled_needed: 0 }), ctx).skilled,
    ).toBe(false);
  });
});

describe("computeIdleQuartile", () => {
  it("includes ties at the cutoff date (quartile_includes_ties_at_cutoff)", () => {
    // 4 volunteers, bottom quartile = floor(4/4)-1 = 0th sorted entry.
    // Two share that oldest date — both must be in the set, not just one.
    const idle = computeIdleQuartile([
      vol({ id: "a", last_assignment_date: "2020-01-01" }),
      vol({ id: "b", last_assignment_date: "2020-01-01" }),
      vol({ id: "c", last_assignment_date: "2025-06-01" }),
      vol({ id: "d", last_assignment_date: "2025-12-01" }),
    ]);
    expect(idle.has("a")).toBe(true);
    expect(idle.has("b")).toBe(true);
    expect(idle.has("c")).toBe(false);
    expect(idle.has("d")).toBe(false);
  });

  it("nulls count as oldest", () => {
    const idle = computeIdleQuartile([
      vol({ id: "never", last_assignment_date: null }),
      vol({ id: "old", last_assignment_date: "2020-01-01" }),
      vol({ id: "mid", last_assignment_date: "2024-01-01" }),
      vol({ id: "new", last_assignment_date: "2025-12-01" }),
    ]);
    expect(idle.has("never")).toBe(true);
    expect(idle.has("new")).toBe(false);
  });
});

describe("spreadsheetConflictKeys", () => {
  it("flags both cells of a double-booking on the same date (spreadsheet_conflict_pairs)", () => {
    // Vick is assigned to two tasks on the same date — both assignments
    // are conflicts, so both cells must be flagged. Catches a bug where
    // only the second-encountered task gets marked.
    const t1 = task({
      id: "A",
      date: "2025-12-01",
      assignments: [assignmentRow("vick", "Vick")],
    });
    const t2 = task({
      id: "B",
      date: "2025-12-01",
      assignments: [assignmentRow("vick", "Vick")],
    });
    const keys = spreadsheetConflictKeys([t1, t2]);
    expect(keys.has("vick|A")).toBe(true);
    expect(keys.has("vick|B")).toBe(true);
  });

  it("does not flag a single assignment per date", () => {
    const t1 = task({
      id: "A",
      date: "2025-12-01",
      assignments: [assignmentRow("vick", "Vick")],
    });
    const t2 = task({
      id: "B",
      date: "2025-12-02",
      assignments: [assignmentRow("vick", "Vick")],
    });
    expect(spreadsheetConflictKeys([t1, t2]).size).toBe(0);
  });

  it("does not flag available-but-unassigned same-date cells", () => {
    // The spreadsheet conflict flag is specifically for double-assignments.
    // Pure availability overlap on a date is shown but not flagged.
    const t1 = task({
      id: "A",
      date: "2025-12-01",
      assignments: [assignmentRow("vick", "Vick")],
    });
    const t2 = task({
      id: "B",
      date: "2025-12-01",
      available: [avail("vick", "Vick")],
    });
    expect(spreadsheetConflictKeys([t1, t2]).size).toBe(0);
  });
});

describe("partitionAvailable", () => {
  it("hides same-date conflicts (conflict_filter_hides_same_date_assigned)", () => {
    const taskA = task({
      id: "A",
      date: "2025-12-01",
      assignments: [assignmentRow("bryan", "Bryan")],
    });
    const taskB = task({
      id: "B",
      date: "2025-12-01",
      available: [avail("bryan", "Bryan"), avail("vick", "Vick")],
    });
    const ctx = buildFairnessContext(
      [vol({ id: "bryan" }), vol({ id: "vick" })],
      [taskA, taskB],
    );
    const { visible, hidden, conflicts } = partitionAvailable(taskB, ctx);
    expect(visible.map((v) => v.person_id)).toEqual(["vick"]);
    expect(hidden.map((v) => v.person_id)).toEqual(["bryan"]);
    expect(conflicts.get("bryan")).toEqual(["A"]);
  });

  it("does not flag conflicts for tasks on different dates", () => {
    const taskA = task({
      id: "A",
      date: "2025-12-01",
      assignments: [assignmentRow("bryan", "Bryan")],
    });
    const taskB = task({
      id: "B",
      date: "2025-12-08",
      available: [avail("bryan", "Bryan")],
    });
    const ctx = buildFairnessContext([vol({ id: "bryan" })], [taskA, taskB]);
    const { visible, hidden } = partitionAvailable(taskB, ctx);
    expect(visible.map((v) => v.person_id)).toEqual(["bryan"]);
    expect(hidden).toEqual([]);
  });
});
