/**
 * Pure helpers backing the /assign page's top-bar gating logic.
 *
 * Kept out of the Svelte route component so the under/over/team-lead +
 * policy decisions can be tested directly without the SvelteKit runtime.
 */

import {
  ASSIGNMENT_POLICY_LABELS,
  type AssignmentPolicy,
} from "$lib/api/types";

/** Subset of `TaskOverviewItem` that the gate cares about. */
export interface PolicyTask {
  assignments: { assignment_id: string }[];
  volunteers_needed: number;
  team_lead_id: string | null;
}

export interface PolicyCounts {
  under: number;
  over: number;
  noLead: number;
}

export function computeCounts(tasks: PolicyTask[]): PolicyCounts {
  let under = 0;
  let over = 0;
  let noLead = 0;
  for (const t of tasks) {
    if (t.assignments.length < t.volunteers_needed) under += 1;
    if (t.assignments.length > t.volunteers_needed) over += 1;
    if (!t.team_lead_id) noLead += 1;
  }
  return { under, over, noLead };
}

/**
 * Message for the top-bar's *counts* slot (Message area 1).
 * Reporting "fewer" overrides reporting "extra" per the user's spec.
 */
export function countsMessage(counts: PolicyCounts): string {
  if (counts.under > 0)
    return "Some tasks have fewer than requested volunteers.";
  if (counts.over > 0) return "Some tasks have extra volunteers.";
  return "All tasks have requested volunteers.";
}

export function countsViolatePolicy(
  counts: PolicyCounts,
  policy: AssignmentPolicy,
): boolean {
  if (policy === "exact") return counts.under > 0 || counts.over > 0;
  if (policy === "over") return counts.under > 0;
  return false; // over_under
}

/**
 * The Save button's enabled state. Requires at least one task and both
 * gates (team-lead + counts/policy) to pass.
 */
export function canSave(
  tasks: PolicyTask[],
  counts: PolicyCounts,
  policy: AssignmentPolicy,
): boolean {
  return (
    tasks.length > 0 &&
    counts.noLead === 0 &&
    !countsViolatePolicy(counts, policy)
  );
}

/**
 * Text for the gate-failure slot (Message area 2). Empty string when
 * the Save button is enabled. Team-lead failure takes precedence over
 * the counts-policy failure when both fail.
 */
export function gateMessage(
  counts: PolicyCounts,
  policy: AssignmentPolicy,
): string {
  if (counts.noLead > 0) {
    const phrase =
      counts.noLead === 1 ? "1 task needs" : `${counts.noLead} tasks need`;
    return `Cannot close assignment: ${phrase} a team lead`;
  }
  if (countsViolatePolicy(counts, policy)) {
    return `Tasks don't have desired volunteers`;
  }
  return "";
}
