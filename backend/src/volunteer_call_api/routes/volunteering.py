"""Volunteering routes — volunteer-facing view of assignments and open calls."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from volunteer_call_api.database import get_db
from volunteer_call_api.dependencies import get_current_user
from volunteer_call_api.models.person import Person
from volunteer_call_api.models.team_assignment import TeamAssignment
from volunteer_call_api.models.volunteer_call import CallStatus, Task
from volunteer_call_api.routes.team_assignments import (
    _stamp_assignments_changed,
    _update_task_status,
)
from volunteer_call_api.schemas.volunteering import AssignmentDeclineRequest, MyAssignment
from volunteer_call_api.services.notifications import (
    drop_from_roster_snapshot,
    notify_decline,
)

router = APIRouter()


async def _my_assignments(user: Person, db: AsyncSession) -> list[MyAssignment]:
    result = await db.execute(
        select(TeamAssignment)
        .where(TeamAssignment.person_id == user.id)
        .options(
            selectinload(TeamAssignment.task).selectinload(Task.volunteer_call),
            selectinload(TeamAssignment.task).selectinload(Task.team_lead),
        )
    )
    assignments = result.scalars().all()

    items = []
    for a in assignments:
        task = a.task
        lead = task.team_lead
        items.append(
            MyAssignment(
                assignment_id=a.id,
                task_id=task.id,
                team_lead_name=(f"{lead.first_name} {lead.last_name}".strip() if lead else None),
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


@router.get("/my-assignments", response_model=list[MyAssignment])
async def get_my_assignments(
    user: Person = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MyAssignment]:
    """Return the current user's team assignments with task details."""
    return await _my_assignments(user, db)


@router.post("/my-assignments/{assignment_id}/decline", response_model=list[MyAssignment])
async def decline_assignment(
    assignment_id: str,
    body: AssignmentDeclineRequest,
    user: Person = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MyAssignment]:
    """Let a volunteer drop a task they're assigned to.

    Hard-deletes the assignment, notifies the team lead and call admin
    immediately (with the volunteer's optional message), and returns the
    volunteer's updated assignment list. Ownership is enforced server-side —
    the assignment must belong to the authenticated user.
    """
    assignment = (
        await db.execute(
            select(TeamAssignment)
            .options(selectinload(TeamAssignment.task).selectinload(Task.volunteer_call))
            .where(TeamAssignment.id == assignment_id)
        )
    ).scalar_one_or_none()
    if assignment is None or assignment.person_id != user.id:
        raise HTTPException(status_code=404, detail="Assignment not found")

    task = assignment.task
    call = task.volunteer_call
    if call.status not in (CallStatus.WAITING, CallStatus.ASSIGNED):
        raise HTTPException(status_code=400, detail="This call is no longer accepting changes")

    call_id = call.id
    task_id = task.id

    await db.delete(assignment)
    await db.flush()
    await _update_task_status(task, db)
    await _stamp_assignments_changed(call_id, db)
    # The decline notice is the lead's signal, so trim the snapshot to avoid a
    # duplicate removal email on the next staff "Send Changed Assignments".
    drop_from_roster_snapshot(call, task_id, user.id)
    await db.commit()

    await notify_decline(
        call_id=call_id,
        task_id=task_id,
        volunteer_id=user.id,
        message=body.message,
        db=db,
    )

    return await _my_assignments(user, db)
