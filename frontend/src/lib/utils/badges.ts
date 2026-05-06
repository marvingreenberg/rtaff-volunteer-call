/** Get CSS class for project status badges */
export function projectStatusBadgeClass(status: string): string {
  const classes: Record<string, string> = {
    intake: "badge-intake",
    assessment: "badge-assessment",
    signed: "badge-signed",
    planning: "badge-planning",
    planned: "badge-planned",
    scheduled: "badge-scheduled",
    in_progress: "badge-progress",
    completed: "badge-completed",
    archived: "badge-archived",
  };
  return classes[status] || "badge-default";
}

/** Get border color CSS variable for project status */
export function projectStatusBorderColor(status: string): string {
  const colors: Record<string, string> = {
    intake: "var(--rt-gray-300)",
    assessment: "var(--rt-blue)",
    signed: "var(--rt-blue)",
    planning: "var(--rt-orange)",
    planned: "var(--rt-orange)",
    scheduled: "var(--rt-green)",
    in_progress: "var(--rt-green)",
    completed: "var(--rt-dark)",
    archived: "var(--rt-gray-300)",
  };
  return colors[status] || "var(--rt-gray-300)";
}

/** Get CSS class for volunteer call/slot status badges */
export function callStatusBadgeClass(status: string): string {
  switch (status) {
    case "draft":
      return "badge-draft";
    case "open":
      return "badge-open";
    case "closed":
      return "badge-closed";
    case "scheduled":
      return "badge-scheduled";
    case "confirmed":
      return "badge-confirmed";
    case "cancelled":
      return "badge-cancelled";
    default:
      return "badge-default";
  }
}

/** Get CSS class for skill category badges */
export function skillBadgeClass(skill: string): string {
  switch (skill) {
    case "skilled":
      return "badge-skilled";
    case "unskilled":
      return "badge-unskilled";
    default:
      return "badge-unknown";
  }
}

const ROLE_LABELS: Record<string, string> = {
  staff: "Staff",
  team_leader: "Team Leader",
  volunteer: "Volunteer",
};

/** Get human-readable label for a role key */
export function roleLabel(role: string): string {
  return ROLE_LABELS[role] || role;
}
