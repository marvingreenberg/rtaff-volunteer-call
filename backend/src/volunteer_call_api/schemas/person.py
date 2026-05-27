"""Pydantic schemas for person endpoints."""

from datetime import date, datetime

from pydantic import BaseModel

from volunteer_call_api.models.person import (
    CalendarKind,
    NotificationDetailLevel,
    NotificationPreference,
    Program,
    RoleType,
    Skill,
    SubscriptionStatus,
)


class ProgramMembership(BaseModel):
    program: Program
    joined_at: datetime
    active: bool

    model_config = {"from_attributes": True}


class PersonCreate(BaseModel):
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    skills: list[Skill] = []
    active: bool = True
    notification_preference: NotificationPreference = NotificationPreference.EMAIL
    notification_detail_level: NotificationDetailLevel = NotificationDetailLevel.FULL
    subscription_status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    notes: str | None = None
    roles: list[RoleType] = []
    programs: list[Program] = []


class PersonUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    skills: list[Skill] | None = None
    active: bool | None = None
    notification_preference: NotificationPreference | None = None
    notification_detail_level: NotificationDetailLevel | None = None
    subscription_status: SubscriptionStatus | None = None
    pause_start: date | None = None
    pause_end: date | None = None
    notes: str | None = None
    roles: list[RoleType] | None = None
    programs: list[Program] | None = None
    calendar_kind: CalendarKind | None = None


class PersonResponse(BaseModel):
    """Public person view. NEVER includes calendar_url (bearer secret)."""

    id: str
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    phone_verified: bool
    skills: list[Skill]
    active: bool
    notification_preference: NotificationPreference
    notification_detail_level: NotificationDetailLevel
    subscription_status: SubscriptionStatus
    pause_start: date | None
    pause_end: date | None
    notes: str | None
    roles: list[RoleType]
    programs: list[ProgramMembership]
    calendar_connected: bool
    calendar_provider: str | None
    calendar_kind: CalendarKind
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PersonListResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    skills: list[Skill]
    active: bool
    roles: list[RoleType]
    programs: list[Program]

    model_config = {"from_attributes": True}


class CalendarConnect(BaseModel):
    """User pastes their private iCal URL. Provider is informational."""

    calendar_url: str
    calendar_provider: str | None = None


class CalendarStatus(BaseModel):
    calendar_connected: bool
    calendar_provider: str | None
    calendar_url_added_at: datetime | None


class CalendarConflict(BaseModel):
    start: datetime
    end: datetime
    summary: str | None


class TaskConflictsResponse(BaseModel):
    """Conflict info per task for the calling user, used by the volunteering page."""

    task_id: str
    has_conflict: bool
    conflicts: list[CalendarConflict]
