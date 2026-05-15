/**
 * Fairness sort + badge helpers for the assign view.
 *
 * Sort key (lexicographic, top to bottom):
 *   1. assignments_this_call  ASC
 *   2. last_assignment_date   ASC, NULL first (never-assigned wins ties)
 *   3. assignments_trailing_3mo ASC
 *   4. first_name, last_name  ASC (case-insensitive, stable final tier)
 *
 * Badges:
 *   🥵  hit self-declared cap for this call (assignments_this_call >= max)
 *   😴  bottom quartile of last_assignment_date within the responding pool
 *       (volunteers with null last_assignment_date are oldest of all)
 *   🛠️  task has skilled_needed > 0 and volunteer has any skill
 *
 * Same-date conflicts are filtered out of the visible Available list and
 * surfaced via a collapsible footer instead.
 */

import type {
  AvailableVolunteer,
  TaskOverviewItem,
  VolunteerOverviewItem,
} from "$lib/api/types";

export interface FairnessContext {
  /** All responding volunteers for the call, keyed by person_id. */
  volunteerById: Map<string, VolunteerOverviewItem>;
  /** Set of person_ids whose last_assignment_date is in the bottom quartile (or null). */
  idleQuartile: Set<string>;
  /** All tasks in the call, for same-date conflict detection. */
  tasks: TaskOverviewItem[];
}

export function buildFairnessContext(
  volunteers: VolunteerOverviewItem[],
  tasks: TaskOverviewItem[],
): FairnessContext {
  const volunteerById = new Map(volunteers.map((v) => [v.person_id, v]));
  return {
    volunteerById,
    idleQuartile: computeIdleQuartile(volunteers),
    tasks,
  };
}

/**
 * "Bottom quartile" of last_assignment_date. Null = oldest (treated as
 * -Infinity). Returns the person_ids comprising the oldest 25% of the
 * responding pool. Tie-breaks: include all ties at the cutoff date.
 */
export function computeIdleQuartile(
  volunteers: VolunteerOverviewItem[],
): Set<string> {
  if (volunteers.length === 0) return new Set();
  const cutoffIndex = Math.max(0, Math.floor(volunteers.length / 4) - 1);
  // Sort ASC by date; null first.
  const sorted = [...volunteers].sort((a, b) => {
    const av = a.last_assignment_date;
    const bv = b.last_assignment_date;
    if (av === bv) return 0;
    if (av === null) return -1;
    if (bv === null) return 1;
    return av < bv ? -1 : 1;
  });
  const cutoffDate = sorted[cutoffIndex].last_assignment_date;
  const result = new Set<string>();
  for (const v of sorted) {
    if (v.last_assignment_date === cutoffDate) {
      result.add(v.person_id);
    } else if (
      cutoffDate !== null &&
      v.last_assignment_date !== null &&
      v.last_assignment_date < cutoffDate
    ) {
      result.add(v.person_id);
    } else if (cutoffDate === null && v.last_assignment_date === null) {
      result.add(v.person_id);
    }
  }
  return result;
}

/** Comparator for the Available list. Lower = higher priority. */
export function fairnessCompare(
  a: AvailableVolunteer,
  b: AvailableVolunteer,
  ctx: FairnessContext,
): number {
  const va = ctx.volunteerById.get(a.person_id);
  const vb = ctx.volunteerById.get(b.person_id);
  // Volunteers without overview metadata fall to the bottom — shouldn't
  // happen in practice but keeps the comparator total.
  if (!va && !vb) return 0;
  if (!va) return 1;
  if (!vb) return -1;
  // 1. assignments_this_call ASC
  if (va.assignments_this_call !== vb.assignments_this_call) {
    return va.assignments_this_call - vb.assignments_this_call;
  }
  // 2. last_assignment_date ASC, null first
  const da = va.last_assignment_date;
  const db = vb.last_assignment_date;
  if (da !== db) {
    if (da === null) return -1;
    if (db === null) return 1;
    return da < db ? -1 : 1;
  }
  // 3. assignments_trailing_3mo ASC
  if (va.assignments_trailing_3mo !== vb.assignments_trailing_3mo) {
    return va.assignments_trailing_3mo - vb.assignments_trailing_3mo;
  }
  // 4. first_name then last_name ASC, case-insensitive
  const fa = va.first_name.toLocaleLowerCase();
  const fb = vb.first_name.toLocaleLowerCase();
  if (fa !== fb) return fa < fb ? -1 : 1;
  const la = va.last_name.toLocaleLowerCase();
  const lb = vb.last_name.toLocaleLowerCase();
  if (la !== lb) return la < lb ? -1 : 1;
  return 0;
}

export interface VolunteerBadges {
  exhausted: boolean; // 🥵
  idle: boolean; // 😴
  skilled: boolean; // 🛠️ (per task)
}

export function badgesFor(
  personId: string,
  task: TaskOverviewItem,
  ctx: FairnessContext,
): VolunteerBadges {
  const v = ctx.volunteerById.get(personId);
  if (!v) return { exhausted: false, idle: false, skilled: false };
  return {
    exhausted: v.assignments_this_call >= v.max_tasks_per_week,
    idle: ctx.idleQuartile.has(personId),
    skilled: task.skilled_needed > 0 && v.skills.length > 0,
  };
}

/**
 * Same-date conflict detection: a volunteer who is *already assigned* to
 * another task on the same date as `task`. Returns the conflicting task
 * ids per volunteer (used for tooltip / footer messaging).
 */
export function sameDateConflicts(
  task: TaskOverviewItem,
  ctx: FairnessContext,
): Map<string, string[]> {
  const out = new Map<string, string[]>();
  if (!task.date) return out;
  for (const other of ctx.tasks) {
    if (other.task_id === task.task_id) continue;
    if (other.date !== task.date) continue;
    for (const a of other.assignments) {
      const arr = out.get(a.person_id) ?? [];
      arr.push(other.task_id);
      out.set(a.person_id, arr);
    }
  }
  return out;
}

/**
 * Split `available_volunteers` into (visible, hidden-by-conflict) lists,
 * with the visible list sorted by fairness.
 */
export function partitionAvailable(
  task: TaskOverviewItem,
  ctx: FairnessContext,
): {
  visible: AvailableVolunteer[];
  hidden: AvailableVolunteer[];
  conflicts: Map<string, string[]>;
} {
  const conflicts = sameDateConflicts(task, ctx);
  const visible: AvailableVolunteer[] = [];
  const hidden: AvailableVolunteer[] = [];
  for (const v of task.available_volunteers) {
    if (conflicts.has(v.person_id)) {
      hidden.push(v);
    } else {
      visible.push(v);
    }
  }
  visible.sort((a, b) => fairnessCompare(a, b, ctx));
  hidden.sort((a, b) => fairnessCompare(a, b, ctx));
  return { visible, hidden, conflicts };
}
