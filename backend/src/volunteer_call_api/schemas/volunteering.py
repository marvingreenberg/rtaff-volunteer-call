"""Schemas for the volunteering view (volunteer-facing)."""

import datetime

from pydantic import BaseModel


class MyAssignment(BaseModel):
    assignment_id: str
    task_id: str
    team_lead_name: str | None
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


class AssignmentDeclineRequest(BaseModel):
    """Body for declining an assigned task. The optional message is forwarded
    to the team lead so the volunteer can explain why they can't make it."""

    message: str | None = None
