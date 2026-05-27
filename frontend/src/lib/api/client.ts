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
  PersonCalendarSummary,
  TaskConflicts,
  LoginRequest,
  LoginResponse,
  VerifyRequest,
  VerifyResponse,
  MyAssignment,
  NotificationResponse,
  Program,
  UnreadCountResponse,
  DashboardResponse,
} from "./types";

const API_BASE = "/api";

/**
 * Read the double-submit CSRF cookie set by the backend. Returns null
 * when we haven't talked to the API yet — the first GET response sets
 * the cookie so subsequent writes can echo it back in the header.
 */
function readCsrfCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

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
  const method = (options.method ?? "GET").toUpperCase();
  const extraHeaders: Record<string, string> = {};
  if (UNSAFE_METHODS.has(method)) {
    const csrf = readCsrfCookie();
    if (csrf) extraHeaders["X-CSRF-Token"] = csrf;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    // The session cookie is HttpOnly; the fetch needs `credentials: 'include'`
    // so the browser actually sends it cross-origin (dev) and same-origin
    // (prod).
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...extraHeaders,
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
    request<VerifyResponse>("/auth/verify", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * Hydrate the current user from the session cookie. Pass `urlToken` to
   * also bootstrap the cookie from a magic-link / invite token in the URL
   * (the backend will set the cookie on first hit). Returns null if no
   * session.
   */
  me: (urlToken?: string | null) => {
    const qs = urlToken ? `?token=${encodeURIComponent(urlToken)}` : "";
    return request<PersonResponse>(`/auth/me${qs}`);
  },

  logout: () =>
    request<{ message: string }>("/auth/logout", { method: "POST" }),
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

  listCalendars: (id: string) =>
    request<PersonCalendarSummary[]>(`/people/${id}/calendars`),

  addCalendar: (id: string, data: CalendarConnect) =>
    request<PersonCalendarSummary>(`/people/${id}/calendars`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  removeCalendar: (id: string, calendarId: string) =>
    request<void>(`/people/${id}/calendars/${calendarId}`, {
      method: "DELETE",
    }),
};

// Volunteer call endpoints
export const volunteerCalls = {
  list: (params?: { status?: string | string[]; program?: Program }) => {
    const query = new URLSearchParams();
    if (params?.status) {
      const statuses = Array.isArray(params.status)
        ? params.status
        : [params.status];
      for (const s of statuses) query.append("status", s);
    }
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
