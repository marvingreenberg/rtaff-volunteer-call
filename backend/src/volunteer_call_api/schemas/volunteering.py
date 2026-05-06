"""Schemas for the volunteering view (volunteer-facing)."""

import datetime

from pydantic import BaseModel


class MyAssignment(BaseModel):
    assignment_id: str
    task_description: str
    address: str | None
    city: str | None
    date: datetime.date | None
    time_start: datetime.time | None
    time_end: datetime.time | None
    role: str
    confirmed: bool
    call_title: str
    call_id: str
