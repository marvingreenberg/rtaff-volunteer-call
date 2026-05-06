"""Reports routes — dashboard stats."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from volunteer_call_api.database import get_db
from volunteer_call_api.models.person import Person, PersonRole, RoleType
from volunteer_call_api.models.team_assignment import TeamAssignment
from volunteer_call_api.models.volunteer_call import VolunteerCall
from volunteer_call_api.schemas.reports import DashboardResponse

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(db: AsyncSession = Depends(get_db)) -> DashboardResponse:
    """Aggregate stats for the volunteer call system."""
    calls_result = await db.execute(
        select(VolunteerCall.status, func.count()).group_by(VolunteerCall.status)
    )
    calls_by_status = {row[0].value: row[1] for row in calls_result.all()}

    volunteer_count_result = await db.execute(
        select(func.count(func.distinct(Person.id)))
        .join(PersonRole)
        .where(PersonRole.role == RoleType.VOLUNTEER, Person.active.is_(True))
    )
    active_volunteers = volunteer_count_result.scalar() or 0

    total_assignments = await db.execute(select(func.count()).select_from(TeamAssignment))

    return DashboardResponse(
        calls_by_status=calls_by_status,
        active_volunteers=active_volunteers,
        total_assignments=total_assignments.scalar() or 0,
    )
