/**
 * Notes-column content for the volunteer-calls list page.
 *
 * Pure helper so the per-status string is testable without mounting the
 * route. Returns an empty string when no notes apply.
 */

import type { VolunteerCallListResponse } from "$lib/api/types";

export function rowNotes(call: VolunteerCallListResponse): string {
  switch (call.status) {
    case "waiting":
      // Shows admins how many volunteers have engaged so they can tell
      // whether to wait, re-send invites, or move to assigning.
      return `${call.volunteers_responded} volunteer${
        call.volunteers_responded === 1 ? "" : "s"
      } responded`;
    case "assigned":
      // Two-clause status: how many slots are filled, and how many
      // tasks are fully staffed. Mirrors the /assign top-bar so the
      // list page reads as a summary of the assign view.
      return (
        `${call.spots_filled}/${call.spots_needed} spots filled · ` +
        `${call.tasks_fully_assigned}/${call.task_count} tasks fully assigned`
      );
    case "open":
    case "archived":
      return "";
    default:
      return "";
  }
}
