"""Pydantic schemas for volunteer availability endpoints."""

import datetime

from pydantic import BaseModel

from volunteer_call_api.models.person import Skill


class AvailabilityCreate(BaseModel):
    person_id: str
    task_id: str | None = None
    available: bool = True
    max_tasks_per_week: int = 2
    max_tasks_per_week_2: int = 2
    notes: str | None = None


class AvailabilityBatchCreate(BaseModel):
    """Submit availability for multiple tasks at once."""

    person_id: str
    task_availabilities: list[dict[str, bool]]  # [{task_id: str, available: bool}]
    max_tasks_per_week: int = 2
    max_tasks_per_week_2: int = 2
    notes: str | None = None


class AvailabilityUpdate(BaseModel):
    available: bool | None = None
    max_tasks_per_week: int | None = None
    max_tasks_per_week_2: int | None = None
    notes: str | None = None


class AvailabilityResponse(BaseModel):
    id: str
    volunteer_call_id: str
    person_id: str
    person_name: str = ""
    person_skills: list[Skill] = []
    task_id: str | None
    available: bool
    max_tasks_per_week: int | None
    max_tasks_per_week_2: int | None
    notes: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
