"""Pydantic schemas for report endpoints."""

from pydantic import BaseModel


class DashboardResponse(BaseModel):
    calls_by_status: dict[str, int]
    active_volunteers: int
    total_assignments: int
