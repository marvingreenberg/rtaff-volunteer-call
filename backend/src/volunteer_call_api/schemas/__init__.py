"""Pydantic schemas for API request/response models."""

from volunteer_call_api.schemas.auth import LoginRequest, LoginResponse, VerifyRequest
from volunteer_call_api.schemas.notification import NotificationResponse, UnreadCountResponse
from volunteer_call_api.schemas.person import (
    PersonCreate,
    PersonListResponse,
    PersonResponse,
    PersonUpdate,
)
from volunteer_call_api.schemas.team_assignment import (
    AvailableVolunteerResponse,
    TeamAssignmentCreate,
    TeamAssignmentResponse,
    TeamAssignmentUpdate,
)
from volunteer_call_api.schemas.volunteer_availability import (
    AvailabilityCreate,
    AvailabilityResponse,
    AvailabilityUpdate,
)
from volunteer_call_api.schemas.volunteer_call import (
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    VolunteerCallCreate,
    VolunteerCallListResponse,
    VolunteerCallResponse,
    VolunteerCallUpdate,
)

__all__ = [
    "LoginRequest",
    "LoginResponse",
    "VerifyRequest",
    "PersonCreate",
    "PersonUpdate",
    "PersonResponse",
    "PersonListResponse",
    "VolunteerCallCreate",
    "VolunteerCallUpdate",
    "VolunteerCallResponse",
    "VolunteerCallListResponse",
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "AvailabilityCreate",
    "AvailabilityUpdate",
    "AvailabilityResponse",
    "TeamAssignmentCreate",
    "TeamAssignmentUpdate",
    "TeamAssignmentResponse",
    "AvailableVolunteerResponse",
    "NotificationResponse",
    "UnreadCountResponse",
]
