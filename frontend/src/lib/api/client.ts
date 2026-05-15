/**
 * API client for the Volunteer Call backend.
 */

import type {
  PersonListResponse,
  PersonResponse,
  PersonCreate,
  PersonUpdate,
  VolunteerCallListResponse,
  VolunteerCallResponse,
  VolunteerCallCreate,
  VolunteerCallUpdate,
  TaskResponse,
  TaskCreate,
  TaskUpdate,
  JobListItem,
  AvailabilityResponse,
  AvailabilityCreate,
  AvailabilityUpdate,
  TeamAssignmentResponse,
  TeamAssignmentCreate,
  TeamAssignmentUpdate,
  AvailableVolunteerResponse,
  SendInvitesResponse,
  AssignmentNoticesResponse,
  AutoAssignTeamLeadsResponse,
  AssignmentOverviewResponse,
  CalendarConnect,
  CalendarStatus,
  TaskConflicts,
  LoginRequest,
  LoginResponse,
  VerifyRequest,
  MyAssignment,
  NotificationResponse,
  Program,
  UnreadCountResponse,
  DashboardResponse,
} from "./types";

const API_BASE = "/api";

function authHeaders(): Record<string, string> {
  if (typeof localStorage !== "undefined") {
    const token = localStorage.getItem("volunteer_call_token");
    if (token) return { Authorization: `Bearer ${token}` };
  }
  return {};
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const text = await response.text();
    let message = text;
    try {
      const json = JSON.parse(text);
      if (json.detail) message = json.detail;
    } catch {
      // not JSON
    }
    throw new ApiError(response.status, response.statusText, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// Auth endpoints
export const auth = {
  login: (data: LoginRequest) =>
    request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  verify: (data: VerifyRequest) =>
    request<PersonResponse>("/auth/verify", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  me: (token: string) =>
    request<PersonResponse>(`/auth/me?token=${encodeURIComponent(token)}`),
};

// People endpoints
export const people = {
  list: (params?: {
    role?: string;
    skill?: string;
    program?: Program;
    active?: boolean;
    search?: string;
  }) => {
    const query = new URLSearchParams();
    if (params?.role) query.set("role", params.role);
    if (params?.skill) query.set("skill", params.skill);
    if (params?.program) query.set("program", params.program);
    if (params?.active !== undefined)
      query.set("active", String(params.active));
    if (params?.search) query.set("search", params.search);
    const qs = query.toString();
    return request<PersonListResponse[]>(`/people${qs ? "?" + qs : ""}`);
  },

  get: (id: string) => request<PersonResponse>(`/people/${id}`),

  create: (data: PersonCreate) =>
    request<PersonResponse>("/people", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: PersonUpdate) =>
    request<PersonResponse>(`/people/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  connectCalendar: (id: string, data: CalendarConnect) =>
    request<CalendarStatus>(`/people/${id}/calendar`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  disconnectCalendar: (id: string) =>
    request<CalendarStatus>(`/people/${id}/calendar`, {
      method: "DELETE",
    }),
};

// Volunteer call endpoints
export const volunteerCalls = {
  list: (params?: { status?: string; program?: Program }) => {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.program) query.set("program", params.program);
    const qs = query.toString();
    return request<VolunteerCallListResponse[]>(
      `/volunteer-calls${qs ? "?" + qs : ""}`,
    );
  },

  get: (id: string) => request<VolunteerCallResponse>(`/volunteer-calls/${id}`),

  create: (data: VolunteerCallCreate) =>
    request<VolunteerCallResponse>("/volunteer-calls", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: VolunteerCallUpdate) =>
    request<VolunteerCallResponse>(`/volunteer-calls/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<void>(`/volunteer-calls/${id}`, { method: "DELETE" }),

  doneAssigning: (id: string) =>
    request<VolunteerCallResponse>(`/volunteer-calls/${id}/done-assigning`, {
      method: "POST",
    }),

  archive: (id: string) =>
    request<VolunteerCallResponse>(`/volunteer-calls/${id}/archive`, {
      method: "POST",
    }),

  addTask: (callId: string, data: TaskCreate) =>
    request<TaskResponse>(`/volunteer-calls/${callId}/tasks`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateTask: (callId: string, taskId: string, data: TaskUpdate) =>
    request<TaskResponse>(`/volunteer-calls/${callId}/tasks/${taskId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteTask: (callId: string, taskId: string) =>
    request<void>(`/volunteer-calls/${callId}/tasks/${taskId}`, {
      method: "DELETE",
    }),

  listJobs: (callId: string) =>
    request<JobListItem[]>(`/volunteer-calls/${callId}/jobs`),

  sendInvites: (callId: string) =>
    request<SendInvitesResponse>(`/volunteer-calls/${callId}/send-invites`, {
      method: "POST",
    }),

  sendAssignmentNotices: (callId: string) =>
    request<AssignmentNoticesResponse>(
      `/volunteer-calls/${callId}/send-assignment-notices`,
      { method: "POST" },
    ),

  assignmentOverview: (callId: string) =>
    request<AssignmentOverviewResponse>(
      `/volunteer-calls/${callId}/assignment-overview`,
    ),

  autoAssignTeamLeads: (callId: string) =>
    request<AutoAssignTeamLeadsResponse>(
      `/volunteer-calls/${callId}/auto-assign-team-leads`,
      { method: "POST" },
    ),

  /** Conflict info per task using the calling user's connected calendar.
   * Returns [] if the user has no calendar URL set. */
  calendarConflicts: (callId: string) =>
    request<TaskConflicts[]>(`/volunteer-calls/${callId}/calendar/conflicts`),
};

// Volunteer availability endpoints
export const volunteerAvailability = {
  list: (callId: string) =>
    request<AvailabilityResponse[]>(`/volunteer-calls/${callId}/availability`),

  submit: (callId: string, data: AvailabilityCreate) =>
    request<AvailabilityResponse>(`/volunteer-calls/${callId}/availability`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (callId: string, availId: string, data: AvailabilityUpdate) =>
    request<AvailabilityResponse>(
      `/volunteer-calls/${callId}/availability/${availId}`,
      {
        method: "PUT",
        body: JSON.stringify(data),
      },
    ),

  withdraw: (callId: string, availId: string) =>
    request<void>(`/volunteer-calls/${callId}/availability/${availId}`, {
      method: "DELETE",
    }),
};

// Team assignment endpoints
export const teamAssignments = {
  list: (callId: string, taskId: string) =>
    request<TeamAssignmentResponse[]>(
      `/volunteer-calls/${callId}/tasks/${taskId}/assignments`,
    ),

  create: (callId: string, taskId: string, data: TeamAssignmentCreate) =>
    request<TeamAssignmentResponse>(
      `/volunteer-calls/${callId}/tasks/${taskId}/assignments`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
    ),

  update: (
    callId: string,
    taskId: string,
    assignmentId: string,
    data: TeamAssignmentUpdate,
  ) =>
    request<TeamAssignmentResponse>(
      `/volunteer-calls/${callId}/tasks/${taskId}/assignments/${assignmentId}`,
      {
        method: "PUT",
        body: JSON.stringify(data),
      },
    ),

  delete: (callId: string, taskId: string, assignmentId: string) =>
    request<void>(
      `/volunteer-calls/${callId}/tasks/${taskId}/assignments/${assignmentId}`,
      {
        method: "DELETE",
      },
    ),

  listAvailable: (callId: string, taskId: string) =>
    request<AvailableVolunteerResponse[]>(
      `/volunteer-calls/${callId}/tasks/${taskId}/available-volunteers`,
    ),
};

// Volunteering endpoints (volunteer-facing)
export const volunteering = {
  myAssignments: () => request<MyAssignment[]>("/volunteering/my-assignments"),
};

// Notification endpoints
export const notifications = {
  list: () => request<NotificationResponse[]>("/notifications"),

  unreadCount: () =>
    request<UnreadCountResponse>("/notifications/unread-count"),

  markRead: (id: string) =>
    request<NotificationResponse>(`/notifications/${id}/read`, {
      method: "PATCH",
    }),
};

// Report endpoints
export const reports = {
  dashboard: () => request<DashboardResponse>("/reports/dashboard"),
};

// Re-export all types
export type * from "./types";
