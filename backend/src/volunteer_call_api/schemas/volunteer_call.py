"""Pydantic schemas for volunteer call and task endpoints."""

import datetime

from pydantic import BaseModel

from volunteer_call_api.models.person import Program, Skill
from volunteer_call_api.models.volunteer_call import CallStatus, TaskStatus


class TaskCreate(BaseModel):
    short_description: str
    date: datetime.date | None = None
    time_start: datetime.time | None = None
    time_end: datetime.time | None = None
    address: str | None = None
    city: str | None = None
    team_lead_id: str | None = None
    volunteers_needed: int = 4
    skilled_needed: int = 0
    notes: str | None = None


class TaskUpdate(BaseModel):
    short_description: str | None = None
    date: datetime.date | None = None
    time_start: datetime.time | None = None
    time_end: datetime.time | None = None
    address: str | None = None
    city: str | None = None
    team_lead_id: str | None = None
    volunteers_needed: int | None = None
    skilled_needed: int | None = None
    status: TaskStatus | None = None
    notes: str | None = None


class TaskResponse(BaseModel):
    id: str
    volunteer_call_id: str
    short_description: str
    date: datetime.date | None
    time_start: datetime.time | None
    time_end: datetime.time | None
    address: str | None
    city: str | None
    team_lead_id: str | None
    team_lead_name: str | None = None
    volunteers_needed: int
    skilled_needed: int
    status: TaskStatus
    notes: str | None
    assigned_count: int = 0
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class VolunteerCallCreate(BaseModel):
    title: str
    program: Program
    status: CallStatus = CallStatus.DRAFT
    notes: str | None = None
    # Convenience for single-task programs (ACR / RAMP / LIFT): caller can
    # supply task fields inline and the server creates one task with the call.
    initial_task: TaskCreate | None = None


class VolunteerCallUpdate(BaseModel):
    title: str | None = None
    status: CallStatus | None = None
    notes: str | None = None
    # `program` deliberately not updateable — once set, it's fixed. Avoids
    # the "what happens to existing availabilities/assignments" question.


class VolunteerCallResponse(BaseModel):
    id: str
    title: str
    program: Program
    status: CallStatus
    notes: str | None
    task_count: int = 0
    tasks: list[TaskResponse] = []
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class JobListItem(BaseModel):
    """Sanitized volunteer-facing view of a task."""

    task_id: str
    date: datetime.date | None
    time_start: datetime.time | None
    time_end: datetime.time | None
    short_description: str
    city: str | None
    volunteers_needed: int
    skilled_needed: int
    assigned_count: int
    program: Program


class TaskAssignment(BaseModel):
    assignment_id: str
    person_id: str
    person_name: str
    initials: str
    skills: list[Skill] = []
    role: str


class AvailableVolunteer(BaseModel):
    """Candidate eligible for a task: marked available, not yet assigned."""

    person_id: str
    person_name: str
    initials: str
    skills: list[Skill] = []


class TaskOverviewItem(BaseModel):
    task_id: str
    short_description: str
    city: str | None
    date: datetime.date | None
    time_start: datetime.time | None
    time_end: datetime.time | None
    volunteers_needed: int
    skilled_needed: int
    status: str
    assignments: list[TaskAssignment] = []
    available_volunteers: list[AvailableVolunteer] = []


class VolunteerOverviewItem(BaseModel):
    person_id: str
    person_name: str
    initials: str
    skills: list[Skill] = []
    phone: str | None = None
    available_task_ids: list[str] = []
    max_tasks_per_week: int = 1
    assignments_this_call: int = 0


class AssignmentOverviewResponse(BaseModel):
    call_id: str
    call_title: str
    tasks: list[TaskOverviewItem] = []
    volunteers: list[VolunteerOverviewItem] = []


class SendInvitesResponse(BaseModel):
    """Result of sending volunteer invitations."""

    volunteers_notified: int
    volunteers_skipped: int


class AssignmentNoticesResponse(BaseModel):
    """Result of sending assignment / thank-you emails after a call closes."""

    assignment_emails: int
    thanks_emails: int


class VolunteerCallListResponse(BaseModel):
    id: str
    title: str
    program: Program
    status: CallStatus
    task_count: int = 0
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
