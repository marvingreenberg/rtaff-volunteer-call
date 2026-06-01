// Pure helpers for the volunteer assigned-tasks / decline flow. Kept out of
// the page component so the branching logic is unit-testable.

import type {
  MyAssignment,
  TaskConflicts,
  VolunteerCallListResponse,
} from "$lib/api/client";

/** Prefilled note a volunteer sends to their team lead when declining a task.
 * `dateLabel` is already formatted by the caller so this stays date-logic-free. */
export function declineMessagePrefill(
  teamLeadName: string | null,
  dateLabel: string,
): string {
  const lead = teamLeadName?.trim();
  return lead
    ? `Sorry ${lead}, I'm unable to come to the project on ${dateLabel}.`
    : `Sorry, I'm unable to come to the project on ${dateLabel}.`;
}

/** Call ids the volunteer is assigned to. Those calls render the assigned-tasks
 * view; the availability grid is suppressed for them. */
export function assignedCallIds(assignments: MyAssignment[]): Set<string> {
  return new Set(assignments.map((a) => a.call_id));
}

/** Calls that should still show the availability grid — the ones the volunteer
 * has NO assignment for. One clear path per action: respond via the grid until
 * you're assigned, then act on assigned tasks. */
export function callsAwaitingResponse(
  openCalls: VolunteerCallListResponse[],
  assignments: MyAssignment[],
): VolunteerCallListResponse[] {
  const assigned = assignedCallIds(assignments);
  return openCalls.filter((c) => !assigned.has(c.id));
}

/** The calendar conflict for a specific assignment, or null when the connected
 * calendar reports none (or no calendar is connected). */
export function conflictFor(
  conflicts: Record<string, Record<string, TaskConflicts>>,
  callId: string,
  taskId: string,
): TaskConflicts | null {
  const c = conflicts[callId]?.[taskId];
  return c && c.has_conflict ? c : null;
}
