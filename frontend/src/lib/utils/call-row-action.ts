/**
 * Decision table for the volunteer-call list page's Action column.
 *
 * A pure function so the table is testable end-to-end without rendering
 * the route. Returns an *array* of decisions because rows in the
 * `assigned` state typically show two stacked buttons (Update + Send).
 *
 * Each call's status + assignments_sent_at + assignments_changed_at +
 * last_task_date + task_count drives which buttons appear.
 */

import type { VolunteerCallListResponse } from "$lib/api/types";

export type RowAction =
  | "send_invites"
  | "assign"
  | "update_assignments"
  | "send_assignments"
  | "send_changed_assignments"
  | "archive";

export interface RowActionDecision {
  /** Button label shown in the cell. Newlines stack the words vertically. */
  label: string;
  /** Click handler key. */
  action: RowAction;
}

/**
 * True if every task in the call has a date that is strictly before
 * `today`. Tasks with no date are ignored (a call with only undated
 * tasks never "passes" because we have no signal). Callers pass `today`
 * (defaults to local midnight) so tests can pin the boundary.
 */
export function lastTaskInPast(
  call: Pick<VolunteerCallListResponse, "last_task_date">,
  today: Date = new Date(),
): boolean {
  if (!call.last_task_date) return false;
  // Anchor both sides at local-midnight so "last task today" reads as
  // "not yet past" — the work might still be happening.
  const last = new Date(call.last_task_date + "T00:00:00");
  const midnight = new Date(
    today.getFullYear(),
    today.getMonth(),
    today.getDate(),
  );
  return last < midnight;
}

/** True iff assignments have been edited since the last Send Assignments. */
function hasUnsentChanges(call: VolunteerCallListResponse): boolean {
  if (call.assignments_sent_at === null) return false;
  if (call.assignments_changed_at === null) return false;
  return (
    new Date(call.assignments_changed_at) > new Date(call.assignments_sent_at)
  );
}

/**
 * Compute the per-row Action column buttons. Order in the returned
 * array is the rendering order top-to-bottom.
 */
export function rowAction(
  call: VolunteerCallListResponse,
  today: Date = new Date(),
): RowActionDecision[] {
  switch (call.status) {
    case "open":
      // Nothing to send until there's at least one task. Hiding the
      // button is the affordance: "go add tasks first".
      return call.task_count === 0
        ? []
        : [{ label: "Send\nCall", action: "send_invites" }];

    case "waiting":
      return [{ label: "Assign\nVolunteers", action: "assign" }];

    case "assigned": {
      // Once the last task date is past, the only sensible action is
      // archive. Both Update and Send disappear — the work is done.
      if (lastTaskInPast(call, today)) {
        return [{ label: "Archive", action: "archive" }];
      }
      // Update is always available while ASSIGNED so admins can fix
      // mistakes / handle drop-outs.
      const actions: RowActionDecision[] = [
        { label: "Update\nAssignments", action: "update_assignments" },
      ];
      if (call.assignments_sent_at === null) {
        actions.push({
          label: "Send\nAssignments",
          action: "send_assignments",
        });
      } else if (hasUnsentChanges(call)) {
        actions.push({
          label: "Send Changed\nAssignments",
          action: "send_changed_assignments",
        });
      }
      // else: sent and current — no Send button (would re-send the same state).
      return actions;
    }

    case "archived":
      return [];

    default:
      return [];
  }
}
