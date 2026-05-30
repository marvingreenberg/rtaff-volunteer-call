/**
 * Pure helpers backing the /assign page's header + the Send-Assignments
 * confirmation. Kept out of the Svelte route component so the under/over/
 * team-lead reckoning can be tested directly without the SvelteKit runtime.
 *
 * The assignment phase no longer *blocks* on these conditions — they're
 * surfaced as warnings (header callout, calls-list banner, and an
 * "Are you sure?" confirmation at Send) rather than gating "Done Assigning".
 */

/** Subset of `TaskOverviewItem` that the warnings care about. */
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

// Emoji prefixes for the two warning lines (per the agreed message format).
const TEAM_LEAD_ICON = "‼️";
const COUNTS_ICON = "⚠️";

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
 * Human-readable warning lines for the current assignment state. Returns
 * one entry per outstanding issue, in priority order (team-lead first):
 *
 *   ‼️ {noLead}/{totalTasks} tasks have no team lead
 *   ⚠️ not all tasks have desired volunteers
 *
 * Empty array when everything is staffed. Callers join with a space for a
 * single-line message (header / banner) or with "\n" for the two-line
 * confirmation popup.
 */
export function assignmentIssues(
  counts: PolicyCounts,
  totalTasks: number,
): string[] {
  const lines: string[] = [];
  if (counts.noLead > 0) {
    lines.push(
      `${TEAM_LEAD_ICON} ${counts.noLead}/${totalTasks} tasks have no team lead`,
    );
  }
  if (counts.under > 0 || counts.over > 0) {
    lines.push(`${COUNTS_ICON} not all tasks have desired volunteers`);
  }
  return lines;
}
