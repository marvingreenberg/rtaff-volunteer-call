"""Schemas for notifications."""

from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    person_id: str
    type: str
    subject: str
    body: str
    link: str | None = None
    read: bool
    call_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    count: int
