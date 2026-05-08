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

export type SkillCategory = "skilled" | "unskilled" | "unknown";
export type RoleType = "staff" | "team_leader" | "volunteer";
export type NotificationPreference = "email" | "sms" | "both";
export type NotificationDetailLevel = "summary" | "full";
export type SubscriptionStatus = "active" | "paused" | "unsubscribed";

export interface PersonCreate {
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  skill_category?: SkillCategory;
  active?: boolean;
  notification_preference?: NotificationPreference;
  notification_detail_level?: NotificationDetailLevel;
  subscription_status?: SubscriptionStatus;
  notes?: string;
  roles?: RoleType[];
}

export interface PersonUpdate {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  skill_category?: SkillCategory;
  active?: boolean;
  notification_preference?: NotificationPreference;
  notification_detail_level?: NotificationDetailLevel;
  subscription_status?: SubscriptionStatus;
  pause_start?: string | null;
  pause_end?: string | null;
  notes?: string;
  roles?: RoleType[];
}

export interface PersonResponse {
  id: string;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  phone_verified: boolean;
  skill_category: SkillCategory;
  active: boolean;
  notification_preference: NotificationPreference;
  notification_detail_level: NotificationDetailLevel;
  subscription_status: SubscriptionStatus;
  pause_start: string | null;
  pause_end: string | null;
  notes: string | null;
  roles: RoleType[];
  created_at: string;
  updated_at: string;
}

export interface PersonListResponse {
  id: string;
  first_name: string;
  last_name: string;
  skill_category: SkillCategory;
  active: boolean;
  roles: RoleType[];
}

// --- Volunteer Calls ---

export type CallStatus = "draft" | "open" | "closed";
export type TaskStatus = "open" | "full" | "cancelled";

export interface VolunteerCallCreate {
  title: string;
  status?: CallStatus;
  notes?: string;
}

export interface VolunteerCallUpdate {
  title?: string;
  status?: CallStatus;
  notes?: string;
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
  person_skill_category: SkillCategory;
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
  person_skill_category: SkillCategory;
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
  skill_category: SkillCategory;
  phone: string | null;
  email: string | null;
}

// --- Assignment Overview ---

export interface TaskAssignment {
  assignment_id: string;
  person_id: string;
  person_name: string;
  initials: string;
  skill_category: string;
  role: string;
}

export interface AvailableVolunteer {
  person_id: string;
  person_name: string;
  initials: string;
  skill_category: string;
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
  skill_category: string;
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
