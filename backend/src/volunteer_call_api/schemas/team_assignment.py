"""Pydantic schemas for team assignment endpoints."""

import datetime

from pydantic import BaseModel

from volunteer_call_api.models.person import SkillCategory
from volunteer_call_api.models.team_assignment import AssignmentRole


class TeamAssignmentCreate(BaseModel):
    person_id: str
    role: AssignmentRole = AssignmentRole.VOLUNTEER
    notes: str | None = None


class TeamAssignmentUpdate(BaseModel):
    role: AssignmentRole | None = None
    confirmed: bool | None = None
    notes: str | None = None


class TeamAssignmentResponse(BaseModel):
    id: str
    task_id: str
    person_id: str
    person_name: str = ""
    person_skill_category: SkillCategory = SkillCategory.UNKNOWN
    person_phone: str | None = None
    person_email: str | None = None
    role: AssignmentRole
    confirmed: bool
    notes: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class AvailableVolunteerResponse(BaseModel):
    person_id: str
    person_name: str
    skill_category: SkillCategory
    phone: str | None
    email: str | None

    model_config = {"from_attributes": True}
