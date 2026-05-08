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
}

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
  /** True iff calendar_url is set on the server. The URL itself never crosses the wire. */
  calendar_connected: boolean;
  calendar_provider: string | null;
  created_at: string;
  updated_at: string;
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

// --- Calendar ---

export interface CalendarConnect {
  calendar_url: string;
  calendar_provider?: string | null;
}

export interface CalendarStatus {
  calendar_connected: boolean;
  calendar_provider: string | null;
  calendar_url_added_at: string | null;
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

export type CallStatus = "draft" | "open" | "closed";
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
  notes?: string;
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
  notes?: string;
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
  created_at: string;
  updated_at: string;
}

export interface VolunteerCallListResponse {
  id: string;
  title: string;
  program: Program;
  status: CallStatus;
  task_count: number;
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
}

// --- Availability ---

export interface AvailabilityCreate {
  person_id: string;
  task_id?: string | null;
  available?: boolean;
  max_tasks_per_week?: number;
  notes?: string;
}

export interface AvailabilityUpdate {
  available?: boolean;
  max_tasks_per_week?: number;
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
  initials: string;
  skills: Skill[];
  role: string;
}

export interface AvailableVolunteer {
  person_id: string;
  person_name: string;
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
  assignments: TaskAssignment[];
  available_volunteers: AvailableVolunteer[];
}

export interface VolunteerOverviewItem {
  person_id: string;
  person_name: string;
  initials: string;
  skills: Skill[];
  phone: string | null;
  available_task_ids: string[];
  max_tasks_per_week: number;
  assignments_this_call: number;
}

export interface AssignmentOverviewResponse {
  call_id: string;
  call_title: string;
  tasks: TaskOverviewItem[];
  volunteers: VolunteerOverviewItem[];
}

export interface SendInvitesResponse {
  volunteers_notified: number;
  volunteers_skipped: number;
}

export interface AssignmentNoticesResponse {
  assignment_emails: number;
  thanks_emails: number;
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
