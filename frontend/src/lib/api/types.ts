/**
 * TypeScript type definitions for the Volunteer Call API.
 */

// --- Auth ---

export interface LoginRequest {
  email: string;
}

export interface LoginResponse {
  message: string;
  demo_token?: string | null;
}

export interface VerifyRequest {
  token: string;
}

/**
 * Current-auth context returned by both `POST /auth/verify` and
 * `GET /auth/me`. `invited_call_id` is set when the presented token is an
 * invite token, so the /volunteering deep-link works whether the user
 * arrives via /verify or hydrates straight from /me.
 */
export interface AuthContextResponse {
  person: PersonResponse;
  invited_call_id: string | null;
}

// /verify keeps its descriptive name; same shape.
export type VerifyResponse = AuthContextResponse;

// --- People ---

export type Skill = "plumbing" | "electrical" | "carpentry" | "hvac";
export type Program = "RTX" | "ACR" | "RAMP" | "LIFT";
export type RoleType = "staff" | "team_leader" | "volunteer";
export type NotificationPreference = "email" | "sms" | "both";
export type NotificationDetailLevel = "summary" | "full";
export type SubscriptionStatus = "active" | "paused" | "unsubscribed";

export const ALL_SKILLS: Skill[] = [
  "plumbing",
  "electrical",
  "carpentry",
  "hvac",
];
export const ALL_PROGRAMS: Program[] = ["RTX", "ACR", "RAMP", "LIFT"];

export const PROGRAM_LABELS: Record<Program, string> = {
  RTX: "RTX",
  ACR: "AC Rescue",
  RAMP: "Ramp",
  LIFT: "Chairlift",
};

/** Programs other than RTX have a single-task workflow. */
export const SINGLE_TASK_PROGRAMS: ReadonlySet<Program> = new Set([
  "ACR",
  "RAMP",
  "LIFT",
]);

/** Default call titles for the single-task programs — admins can edit. */
const SINGLE_TASK_PROGRAM_TITLES: Record<Program, string> = {
  RTX: "",
  ACR: "AC Rescue call",
  RAMP: "Ramp Install call",
  LIFT: "Chairlift call",
};

const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

/**
 * Suggest a default call title from program (and, for RTX, today's date —
 * used to anchor the next two-week RTX cycle). Returns an empty string only
 * when the date-based computation can't run.
 *
 * RTX format: "RTX Call <Month> <Day> - [<Month> ]<Day>". The window starts
 * on the upcoming Monday (today if today is a Monday) and ends 11 days
 * later (the 2nd Friday). The closing month name is omitted when both ends
 * fall in the same month, since "May 11 - 22" reads cleaner than "May 11 -
 * May 22"; month-crossings like "April 27 - May 8" keep both names so the
 * end date isn't ambiguous.
 *
 * `today` is injectable so tests aren't tied to wall-clock time.
 */
export function suggestCallTitle(
  program: Program,
  today: Date = new Date(),
): string {
  if (program === "RTX") {
    const dow = today.getDay(); // 0=Sun..6=Sat
    const offsetToMon = dow === 0 ? 1 : dow === 1 ? 0 : 8 - dow;
    const monday = new Date(today);
    monday.setDate(today.getDate() + offsetToMon);
    const friday = new Date(monday);
    friday.setDate(monday.getDate() + 11);
    const startMonth = MONTH_NAMES[monday.getMonth()];
    const endMonth = MONTH_NAMES[friday.getMonth()];
    const start = `${startMonth} ${monday.getDate()}`;
    const end =
      startMonth === endMonth
        ? `${friday.getDate()}`
        : `${endMonth} ${friday.getDate()}`;
    return `RTX Call ${start} - ${end}`;
  }
  return SINGLE_TASK_PROGRAM_TITLES[program];
}

export interface ProgramMembership {
  program: Program;
  joined_at: string;
  active: boolean;
}

export interface PersonCreate {
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  skills?: Skill[];
  active?: boolean;
  notification_preference?: NotificationPreference;
  notification_detail_level?: NotificationDetailLevel;
  subscription_status?: SubscriptionStatus;
  notes?: string;
  roles?: RoleType[];
  programs?: Program[];
}

export interface PersonUpdate {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  skills?: Skill[];
  active?: boolean;
  notification_preference?: NotificationPreference;
  notification_detail_level?: NotificationDetailLevel;
  subscription_status?: SubscriptionStatus;
  pause_start?: string | null;
  pause_end?: string | null;
  notes?: string;
  roles?: RoleType[];
  programs?: Program[];
  calendar_kind?: CalendarKind;
}

export type CalendarKind = "google" | "apple" | "outlook" | "other";

export interface PersonResponse {
  id: string;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  phone_verified: boolean;
  skills: Skill[];
  active: boolean;
  notification_preference: NotificationPreference;
  notification_detail_level: NotificationDetailLevel;
  subscription_status: SubscriptionStatus;
  pause_start: string | null;
  pause_end: string | null;
  notes: string | null;
  roles: RoleType[];
  programs: ProgramMembership[];
  /**
   * Connected iCal feeds. Each row carries id + provider + label +
   * added_at — never the URL itself (the URL is a bearer secret on
   * the server). UI derives "calendar_connected" from
   * `calendars.length > 0`.
   */
  calendars: PersonCalendarSummary[];
  /** Preferred calendar app for "Add to calendar" deeplinks. */
  calendar_kind: CalendarKind;
  created_at: string;
  updated_at: string;
}

export interface PersonCalendarSummary {
  id: string;
  calendar_provider: string | null;
  label: string | null;
  added_at: string;
}

export interface PersonListResponse {
  id: string;
  first_name: string;
  last_name: string;
  skills: Skill[];
  active: boolean;
  roles: RoleType[];
  programs: Program[];
}

export interface PersonPageResponse {
  items: PersonListResponse[];
  /** Matching-records count for the same WHERE — not limited by start/count. */
  total: number;
  start: number;
  count: number;
}

// --- Calendar ---

export interface CalendarConnect {
  calendar_url: string;
  calendar_provider?: string | null;
  label?: string | null;
}

export interface CalendarConflict {
  start: string;
  end: string;
  summary: string | null;
}

export interface TaskConflicts {
  task_id: string;
  has_conflict: boolean;
  conflicts: CalendarConflict[];
}

// --- Volunteer Calls ---

export type CallStatus = "open" | "waiting" | "assigned" | "archived";
export type TaskStatus = "open" | "full" | "cancelled";

export interface VolunteerCallCreate {
  title: string;
  program: Program;
  status?: CallStatus;
  notes?: string;
  /** For ACR/RAMP/LIFT: caller can pass an inline task so the create
   * form is one screen. RTX usually omits this and adds tasks later. */
  initial_task?: TaskCreate | null;
}

export interface VolunteerCallUpdate {
  title?: string;
  status?: CallStatus;
  notes?: string;
  /** Note: program is intentionally absent — once set, a call's
   * program is immutable. */
}

export interface TaskCreate {
  short_description: string;
  date?: string | null;
  time_start?: string | null;
  time_end?: string | null;
  address?: string | null;
  city?: string | null;
  team_lead_id?: string | null;
  volunteers_needed?: number;
  skilled_needed?: number;
  notes?: string | null;
}

export interface TaskUpdate {
  short_description?: string;
  date?: string | null;
  time_start?: string | null;
  time_end?: string | null;
  address?: string | null;
  city?: string | null;
  team_lead_id?: string | null;
  volunteers_needed?: number;
  skilled_needed?: number;
  status?: TaskStatus;
  notes?: string | null;
}

export interface TaskAssigneeSummary {
  person_id: string;
  first_name: string;
  last_name: string;
  initials: string;
  is_team_lead: boolean;
}

export interface TaskResponse {
  id: string;
  volunteer_call_id: string;
  short_description: string;
  date: string | null;
  time_start: string | null;
  time_end: string | null;
  address: string | null;
  city: string | null;
  team_lead_id: string | null;
  team_lead_name: string | null;
  volunteers_needed: number;
  skilled_needed: number;
  status: TaskStatus;
  notes: string | null;
  assigned_count: number;
  assignees: TaskAssigneeSummary[];
  created_at: string;
  updated_at: string;
}

export interface VolunteerCallResponse {
  id: string;
  title: string;
  program: Program;
  status: CallStatus;
  notes: string | null;
  task_count: number;
  tasks: TaskResponse[];
  /** Stamped when Send Assignments fires; null until then. */
  assignments_sent_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface VolunteerCallListResponse {
  id: string;
  title: string;
  program: Program;
  status: CallStatus;
  task_count: number;
  assignments_sent_at: string | null;
  assignments_changed_at: string | null;
  /** Distinct people with any availability record on this call. */
  volunteers_responded: number;
  /** Sum of len(task.assignments) across non-cancelled tasks. */
  spots_filled: number;
  /** Sum of task.volunteers_needed. */
  spots_needed: number;
  /** Tasks where assigned >= volunteers_needed. */
  tasks_fully_assigned: number;
  /** Max(task.date) across the call's tasks; null when no tasks have dates. */
  last_task_date: string | null;
  created_at: string;
  updated_at: string;
}

// --- Jobs (volunteer-facing) ---

export interface JobListItem {
  task_id: string;
  date: string | null;
  time_start: string | null;
  time_end: string | null;
  short_description: string;
  city: string | null;
  volunteers_needed: number;
  skilled_needed: number;
  assigned_count: number;
  program: Program;
  notes: string | null;
}

// --- Availability ---

export interface AvailabilityCreate {
  person_id: string;
  task_id?: string | null;
  available?: boolean;
  max_tasks_per_week?: number;
  max_tasks_per_week_2?: number;
  notes?: string;
}

export interface AvailabilityUpdate {
  available?: boolean;
  max_tasks_per_week?: number;
  max_tasks_per_week_2?: number;
  notes?: string;
}

export interface AvailabilityResponse {
  id: string;
  volunteer_call_id: string;
  person_id: string;
  person_name: string;
  person_skills: Skill[];
  task_id: string | null;
  available: boolean;
  max_tasks_per_week: number | null;
  max_tasks_per_week_2: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// --- Team Assignments ---

export interface TeamAssignmentCreate {
  person_id: string;
  role?: string;
  notes?: string;
}

export interface TeamAssignmentUpdate {
  role?: string;
  confirmed?: boolean;
  notes?: string;
}

export interface TeamAssignmentResponse {
  id: string;
  task_id: string;
  person_id: string;
  person_name: string;
  person_skills: Skill[];
  person_phone: string | null;
  person_email: string | null;
  role: string;
  confirmed: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface AvailableVolunteerResponse {
  person_id: string;
  person_name: string;
  skills: Skill[];
  phone: string | null;
  email: string | null;
}

// --- Assignment Overview ---

export interface TaskAssignment {
  assignment_id: string;
  person_id: string;
  person_name: string;
  first_name: string;
  last_name: string;
  initials: string;
  skills: Skill[];
  role: string;
}

export interface AvailableVolunteer {
  person_id: string;
  person_name: string;
  first_name: string;
  last_name: string;
  initials: string;
  skills: Skill[];
}

export interface TaskOverviewItem {
  task_id: string;
  short_description: string;
  city: string | null;
  date: string | null;
  time_start: string | null;
  time_end: string | null;
  volunteers_needed: number;
  skilled_needed: number;
  status: string;
  notes: string | null;
  team_lead_id: string | null;
  team_lead_name: string | null;
  assignments: TaskAssignment[];
  available_volunteers: AvailableVolunteer[];
}

export interface VolunteerOverviewItem {
  person_id: string;
  person_name: string;
  first_name: string;
  last_name: string;
  initials: string;
  skills: Skill[];
  phone: string | null;
  available_task_ids: string[];
  max_tasks_per_week: number;
  max_tasks_per_week_2: number;
  assignments_this_call: number;
  last_assignment_date: string | null;
  assignments_trailing_3mo: number;
}

export interface AssignmentOverviewResponse {
  call_id: string;
  call_title: string;
  call_status: CallStatus;
  tasks: TaskOverviewItem[];
  volunteers: VolunteerOverviewItem[];
}

export interface SendInvitesResponse {
  volunteers_notified: number;
  volunteers_skipped: number;
}

export interface AutoAssignTeamLeadsResponse {
  tasks_updated: number;
  tasks_skipped: number;
  assigned_lead_ids: string[];
}

export interface AssignmentNoticesResponse {
  assignment_emails: number;
  thanks_emails: number;
  team_lead_emails: number;
  removal_emails: number;
}

// --- Volunteering (volunteer-facing) ---

export interface MyAssignment {
  assignment_id: string;
  task_description: string;
  address: string | null;
  city: string | null;
  date: string | null;
  time_start: string | null;
  time_end: string | null;
  role: string;
  confirmed: boolean;
  call_title: string;
  call_id: string;
}

// --- Notifications ---

export interface NotificationResponse {
  id: string;
  person_id: string;
  type: string;
  subject: string;
  body: string;
  link: string | null;
  read: boolean;
  call_id: string | null;
  created_at: string;
}

export interface UnreadCountResponse {
  count: number;
}

// --- Reports ---

export interface DashboardResponse {
  calls_by_status: Record<string, number>;
  active_volunteers: number;
  total_assignments: number;
}
