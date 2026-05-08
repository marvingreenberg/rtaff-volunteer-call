"""Team assignment routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from volunteer_call_api.database import get_db
from volunteer_call_api.models.person import Person, RoleType
from volunteer_call_api.models.team_assignment import TeamAssignment
from volunteer_call_api.models.volunteer_availability import VolunteerAvailability
from volunteer_call_api.models.volunteer_call import Task, TaskStatus
from volunteer_call_api.routes.helpers import apply_partial_update, get_one_or_404
from volunteer_call_api.schemas.team_assignment import (
    AvailableVolunteerResponse,
    TeamAssignmentCreate,
    TeamAssignmentResponse,
    TeamAssignmentUpdate,
)

router = APIRouter()


def _assignment_response(assignment: TeamAssignment) -> TeamAssignmentResponse:
    person = assignment.person
    name = f"{person.first_name} {person.last_name}" if person else ""
    return TeamAssignmentResponse(
        id=assignment.id,
        task_id=assignment.task_id,
        person_id=assignment.person_id,
        person_name=name,
        person_skills=list(person.skills) if person else [],
        person_phone=person.phone if person else None,
        person_email=person.email if person else None,
        role=assignment.role,
        confirmed=assignment.confirmed,
        notes=assignment.notes,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )


async def _get_task_or_404(call_id: str, task_id: str, db: AsyncSession) -> Task:
    query = (
        select(Task)
        .options(selectinload(Task.assignments))
        .where(Task.id == task_id, Task.volunteer_call_id == call_id)
    )
    return await get_one_or_404(db, query, "Task not found")


async def _update_task_status(task: Task, db: AsyncSession) -> None:
    """Auto-update task status based on assignment count."""
    result = await db.execute(select(TeamAssignment).where(TeamAssignment.task_id == task.id))
    assigned = len(result.scalars().all())
    if task.status != TaskStatus.CANCELLED:
        task.status = TaskStatus.FULL if assigned >= task.volunteers_needed else TaskStatus.OPEN


@router.post(
    "/{call_id}/tasks/{task_id}/assignments",
    response_model=TeamAssignmentResponse,
    status_code=201,
)
async def create_assignment(
    call_id: str,
    task_id: str,
    body: TeamAssignmentCreate,
    db: AsyncSession = Depends(get_db),
) -> TeamAssignmentResponse:
    task = await _get_task_or_404(call_id, task_id, db)
    person_result = await db.execute(select(Person).where(Person.id == body.person_id))
    if person_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="Person not found")
    assignment = TeamAssignment(
        task_id=task.id,
        person_id=body.person_id,
        role=body.role,
        notes=body.notes,
    )
    db.add(assignment)
    await db.flush()
    await _update_task_status(task, db)
    await db.commit()
    result = await db.execute(
        select(TeamAssignment)
        .options(selectinload(TeamAssignment.person))
        .where(TeamAssignment.id == assignment.id)
    )
    assignment = result.scalar_one()
    return _assignment_response(assignment)


@router.get(
    "/{call_id}/tasks/{task_id}/assignments",
    response_model=list[TeamAssignmentResponse],
)
async def list_assignments(
    call_id: str, task_id: str, db: AsyncSession = Depends(get_db)
) -> list[TeamAssignmentResponse]:
    await _get_task_or_404(call_id, task_id, db)
    result = await db.execute(
        select(TeamAssignment)
        .options(selectinload(TeamAssignment.person))
        .where(TeamAssignment.task_id == task_id)
    )
    return [_assignment_response(a) for a in result.scalars().all()]


@router.put(
    "/{call_id}/tasks/{task_id}/assignments/{assignment_id}",
    response_model=TeamAssignmentResponse,
)
async def update_assignment(
    call_id: str,
    task_id: str,
    assignment_id: str,
    body: TeamAssignmentUpdate,
    db: AsyncSession = Depends(get_db),
) -> TeamAssignmentResponse:
    await _get_task_or_404(call_id, task_id, db)
    result = await db.execute(
        select(TeamAssignment)
        .options(selectinload(TeamAssignment.person))
        .where(TeamAssignment.id == assignment_id, TeamAssignment.task_id == task_id)
    )
    assignment = result.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    apply_partial_update(assignment, body, ["role", "confirmed", "notes"])
    await db.commit()
    await db.refresh(assignment)
    result = await db.execute(
        select(TeamAssignment)
        .options(selectinload(TeamAssignment.person))
        .where(TeamAssignment.id == assignment.id)
    )
    assignment = result.scalar_one()
    return _assignment_response(assignment)


@router.delete("/{call_id}/tasks/{task_id}/assignments/{assignment_id}", status_code=204)
async def delete_assignment(
    call_id: str,
    task_id: str,
    assignment_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    task = await _get_task_or_404(call_id, task_id, db)
    result = await db.execute(
        select(TeamAssignment).where(
            TeamAssignment.id == assignment_id, TeamAssignment.task_id == task_id
        )
    )
    assignment = result.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    await db.delete(assignment)
    await db.flush()
    await _update_task_status(task, db)
    await db.commit()


@router.get(
    "/{call_id}/tasks/{task_id}/available-volunteers",
    response_model=list[AvailableVolunteerResponse],
)
async def list_available_volunteers(
    call_id: str, task_id: str, db: AsyncSession = Depends(get_db)
) -> list[AvailableVolunteerResponse]:
    await _get_task_or_404(call_id, task_id, db)

    assigned_result = await db.execute(
        select(TeamAssignment.person_id).where(TeamAssignment.task_id == task_id)
    )
    assigned_ids = {row[0] for row in assigned_result.all()}

    avail_result = await db.execute(
        select(VolunteerAvailability)
        .options(selectinload(VolunteerAvailability.person).selectinload(Person.roles))
        .where(
            VolunteerAvailability.volunteer_call_id == call_id,
            VolunteerAvailability.task_id == task_id,
            VolunteerAvailability.available.is_(True),
        )
    )
    availabilities = avail_result.scalars().all()

    candidates: list[AvailableVolunteerResponse] = []
    for avail in availabilities:
        person = avail.person
        if person.id in assigned_ids or not person.active:
            continue
        has_volunteer_role = any(r.role == RoleType.VOLUNTEER for r in person.roles)
        has_leader_role = any(r.role == RoleType.TEAM_LEADER for r in person.roles)
        if not has_volunteer_role and not has_leader_role:
            continue
        candidates.append(
            AvailableVolunteerResponse(
                person_id=person.id,
                person_name=f"{person.first_name} {person.last_name}",
                skills=list(person.skills),
                phone=person.phone,
                email=person.email,
            )
        )

    # Skilled (any tag) volunteers float to the top, then alpha by name.
    candidates.sort(key=lambda c: (not c.skills, c.person_name))
    return candidates
