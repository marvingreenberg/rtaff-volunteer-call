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

/** Get CSS class for volunteer call/slot status badges. Re-uses the
 * existing draft/open/full/cancelled palette colors rather than minting
 * new ones: open→gray, waiting→blue, assigned→green, archived→red-ish.
 */
export function callStatusBadgeClass(status: string): string {
  switch (status) {
    case "open":
      return "badge-draft";
    case "waiting":
      return "badge-open";
    case "assigned":
      return "badge-full";
    case "archived":
      return "badge-cancelled";
    // Slot/task badges share this helper today.
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

/** Get CSS class for a single skill chip. */
export function skillBadgeClass(skill: string): string {
  switch (skill) {
    case "plumbing":
    case "electrical":
    case "carpentry":
    case "hvac":
      return "badge-skilled";
    default:
      return "badge-default";
  }
}

const SKILL_LABELS: Record<string, string> = {
  plumbing: "Plumbing",
  electrical: "Electrical",
  carpentry: "Carpentry",
  hvac: "HVAC",
};

/** Human-readable label for a skill key. */
export function skillLabel(skill: string): string {
  return SKILL_LABELS[skill] || skill;
}

const PROGRAM_LABELS: Record<string, string> = {
  RTX: "RTX",
  ACR: "AC Rescue",
  RAMP: "Ramp",
  LIFT: "Chairlift",
};

/** Human-readable label for a program key. */
export function programLabel(program: string): string {
  return PROGRAM_LABELS[program] || program;
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
