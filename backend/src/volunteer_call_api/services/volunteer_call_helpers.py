"""Helper functions for volunteer call routes."""

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from volunteer_call_api.models.team_assignment import TeamAssignment
from volunteer_call_api.models.volunteer_call import Task, VolunteerCall
from volunteer_call_api.routes.helpers import get_one_or_404
from volunteer_call_api.schemas.volunteer_call import (
    TaskAssigneeSummary,
    TaskResponse,
    VolunteerCallListResponse,
    VolunteerCallResponse,
)

# Sentinels for the task sort key — None values sort after real ones.
_DATE_SENTINEL = datetime.date.max
_TIME_SENTINEL = datetime.time.max


def _initials(first_name: str, last_name: str) -> str:
    first = first_name[0].upper() if first_name else ""
    last = last_name[0].upper() if last_name else ""
    return first + last


def _sorted_tasks(tasks: list[Task]) -> list[Task]:
    """Tasks shown chronologically (ASC date, NULLs last) everywhere — task
    list, emails, call detail, assign view. Stable secondary sort by
    created_at so two tasks on the same date keep a predictable order.
    """
    return sorted(
        tasks,
        key=lambda t: (
            t.date is None,
            t.date or _DATE_SENTINEL,
            t.time_start or _TIME_SENTINEL,
            t.created_at,
        ),
    )


def task_response(task: Task) -> TaskResponse:
    team_lead_name = None
    if task.team_lead:
        team_lead_name = f"{task.team_lead.first_name} {task.team_lead.last_name}"

    # Assignees sorted by first name for stable chip order in the UI.
    # Team lead floated to the front so it reads "lead first, then crew".
    assignees: list[TaskAssigneeSummary] = []
    for a in task.assignments:
        p = a.person
        if p is None:
            continue
        assignees.append(
            TaskAssigneeSummary(
                person_id=p.id,
                first_name=p.first_name,
                last_name=p.last_name,
                initials=_initials(p.first_name, p.last_name),
                is_team_lead=(p.id == task.team_lead_id),
            )
        )
    assignees.sort(key=lambda a: (not a.is_team_lead, a.first_name.lower()))

    return TaskResponse(
        id=task.id,
        volunteer_call_id=task.volunteer_call_id,
        short_description=task.short_description,
        date=task.date,
        time_start=task.time_start,
        time_end=task.time_end,
        address=task.address,
        city=task.city,
        team_lead_id=task.team_lead_id,
        team_lead_name=team_lead_name,
        volunteers_needed=task.volunteers_needed,
        skilled_needed=task.skilled_needed,
        status=task.status,
        notes=task.notes,
        assigned_count=len(task.assignments),
        assignees=assignees,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def call_response(call: VolunteerCall) -> VolunteerCallResponse:
    tasks = [task_response(t) for t in _sorted_tasks(call.tasks)]
    return VolunteerCallResponse(
        id=call.id,
        title=call.title,
        program=call.program,
        status=call.status,
        notes=call.notes,
        task_count=len(tasks),
        tasks=tasks,
        assignments_sent_at=call.assignments_sent_at,
        created_at=call.created_at,
        updated_at=call.updated_at,
    )


def call_list_response(call: VolunteerCall) -> VolunteerCallListResponse:
    # Aggregates used by the list page's Notes column + Action button
    # decisions. Computed in Python over already-eager-loaded relations
    # (tasks → assignments + availabilities). Cheap at current scale.
    spots_filled = 0
    spots_needed = 0
    tasks_fully_assigned = 0
    last_task_date = None
    for t in call.tasks:
        assigned = len(t.assignments)
        spots_filled += assigned
        spots_needed += t.volunteers_needed
        if assigned >= t.volunteers_needed:
            tasks_fully_assigned += 1
        if t.date is not None and (last_task_date is None or t.date > last_task_date):
            last_task_date = t.date
    volunteers_responded = len({a.person_id for a in call.availabilities})

    return VolunteerCallListResponse(
        id=call.id,
        title=call.title,
        program=call.program,
        status=call.status,
        task_count=len(call.tasks),
        assignments_sent_at=call.assignments_sent_at,
        assignments_changed_at=call.assignments_changed_at,
        volunteers_responded=volunteers_responded,
        spots_filled=spots_filled,
        spots_needed=spots_needed,
        tasks_fully_assigned=tasks_fully_assigned,
        last_task_date=last_task_date,
        created_at=call.created_at,
        updated_at=call.updated_at,
    )


async def get_call_or_404(call_id: str, db: AsyncSession) -> VolunteerCall:
    query = (
        select(VolunteerCall)
        .options(
            # Eager-load assignees so task_response can render the
            # assignee chips without lazy-loading per task.
            selectinload(VolunteerCall.tasks)
            .selectinload(Task.assignments)
            .selectinload(TeamAssignment.person),
            selectinload(VolunteerCall.tasks).selectinload(Task.team_lead),
        )
        .where(VolunteerCall.id == call_id)
    )
    return await get_one_or_404(db, query, "Volunteer call not found")
