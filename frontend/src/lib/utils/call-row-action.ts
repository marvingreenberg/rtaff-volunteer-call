/**
 * Decision table for the volunteer-call list page's Action column.
 *
 * Encoded as a pure function so the table is testable end-to-end
 * without rendering the route. Each call's status + assignments_sent_at
 * + task_count drives at most one button per row.
 */

import type { VolunteerCallListResponse } from "$lib/api/types";

export type RowAction =
  | "send_invites"
  | "assign"
  | "send_assignments"
  | "archive";

export interface RowActionDecision {
  /** Button label shown in the cell. Empty string when no button. */
  label: string;
  /** Click handler key; null when no button (cell renders empty). */
  action: RowAction | null;
}

const NO_ACTION: RowActionDecision = { label: "", action: null };

export function rowAction(call: VolunteerCallListResponse): RowActionDecision {
  switch (call.status) {
    case "open":
      // A brand-new call with no tasks has nothing to send — hide the
      // button entirely rather than showing a "Send Call" that would
      // either error or send an empty invite.
      return call.task_count === 0
        ? NO_ACTION
        : { label: "Send Call", action: "send_invites" };
    case "waiting":
      return { label: "Assign Volunteers", action: "assign" };
    case "assigned":
      // Two sub-states: notices not yet sent → Send Assignments;
      // already sent → Archive. The presence of assignments_sent_at
      // is the only signal.
      return call.assignments_sent_at === null
        ? { label: "Send Assignments", action: "send_assignments" }
        : { label: "Archive", action: "archive" };
    case "archived":
      return NO_ACTION;
    default:
      return NO_ACTION;
  }
}
