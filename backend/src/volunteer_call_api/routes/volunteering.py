"""Volunteering routes — volunteer-facing view of assignments and open calls."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from volunteer_call_api.database import get_db
from volunteer_call_api.dependencies import get_current_user
from volunteer_call_api.models.person import Person
from volunteer_call_api.models.team_assignment import TeamAssignment
from volunteer_call_api.models.volunteer_call import Task
from volunteer_call_api.schemas.volunteering import MyAssignment

router = APIRouter()


@router.get("/my-assignments", response_model=list[MyAssignment])
async def get_my_assignments(
    user: Person = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MyAssignment]:
    """Return the current user's team assignments with task details."""
    result = await db.execute(
        select(TeamAssignment)
        .where(TeamAssignment.person_id == user.id)
        .options(
            selectinload(TeamAssignment.task).selectinload(Task.volunteer_call),
        )
    )
    assignments = result.scalars().all()

    items = []
    for a in assignments:
        task = a.task
        items.append(
            MyAssignment(
                assignment_id=a.id,
                task_description=task.short_description,
                address=task.address,
                city=task.city,
                date=task.date,
                time_start=task.time_start,
                time_end=task.time_end,
                role=a.role.value,
                confirmed=a.confirmed,
                call_title=task.volunteer_call.title,
                call_id=task.volunteer_call.id,
            )
        )
    return items
