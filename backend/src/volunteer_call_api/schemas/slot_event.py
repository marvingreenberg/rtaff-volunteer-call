"""Schemas for slot events."""

from datetime import date

from pydantic import BaseModel


class SlotEventCreate(BaseModel):
    event_type: str  # postponed, cancelled, rescheduled
    reason: str
    new_date: date | None = None
    created_by_id: str | None = None
    cc_people: list[str] | None = None  # list of person IDs to CC


class MockNotification(BaseModel):
    person_name: str
    email: str
    role: str  # "assigned" or "cc"


class SlotEventResponse(BaseModel):
    id: str
    task_id: str
    event_type: str
    reason: str
    new_date: date | None
    created_by_id: str | None
    created_by_name: str | None = None
    notified_people: list[dict[str, str]]
    cc_people: list[dict[str, str]]
    created_at: str

    model_config = {"from_attributes": True}


class SlotEventCreateResponse(BaseModel):
    event: SlotEventResponse
    mock_notifications: list[MockNotification]
