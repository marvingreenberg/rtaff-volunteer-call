"""Calendar URL connection + per-call conflict computation.

The user pastes their private iCal URL (Google "Secret address in iCal
format" or Apple iCloud public-share URL); we treat the URL itself as
a bearer secret. PUT/DELETE are self-only (or staff acting on
another user's profile via people routes). The conflicts endpoint is
self-only — never expose someone else's calendar contents.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from volunteer_call_api.database import get_db
from volunteer_call_api.dependencies import get_current_user
from volunteer_call_api.models.person import Person, RoleType
from volunteer_call_api.models.volunteer_call import Task
from volunteer_call_api.schemas.person import (
    CalendarConflict,
    CalendarConnect,
    CalendarStatus,
    TaskConflictsResponse,
)
from volunteer_call_api.services.calendar import (
    CalendarValidationError,
    get_events_for_person,
    invalidate_person_cache,
    overlaps,
    validate_calendar_url,
)

# Mounted at /api/people; handles per-person connect/disconnect.
people_router = APIRouter()
# Mounted at /api/volunteer-calls; handles per-call conflict lookup.
calls_router = APIRouter()


def _is_staff(user: Person) -> bool:
    return any(r.role == RoleType.STAFF for r in user.roles)


def _status(person: Person) -> CalendarStatus:
    return CalendarStatus(
        calendar_connected=person.calendar_url is not None,
        calendar_provider=person.calendar_provider,
        calendar_url_added_at=person.calendar_url_added_at,
    )


async def _get_person_for_self_or_staff(person_id: str, user: Person, db: AsyncSession) -> Person:
    if person_id != user.id and not _is_staff(user):
        raise HTTPException(status_code=403, detail="Forbidden")
    result = await db.execute(
        select(Person).options(selectinload(Person.roles)).where(Person.id == person_id)
    )
    person = result.scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


@people_router.put("/{person_id}/calendar", response_model=CalendarStatus)
async def connect_calendar(
    person_id: str,
    body: CalendarConnect,
    user: Person = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarStatus:
    person = await _get_person_for_self_or_staff(person_id, user, db)
    try:
        await validate_calendar_url(body.calendar_url)
    except CalendarValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    person.calendar_url = body.calendar_url
    person.calendar_provider = body.calendar_provider
    person.calendar_url_added_at = datetime.now(timezone.utc)
    invalidate_person_cache(person.id)
    await db.commit()
    await db.refresh(person)
    return _status(person)


@people_router.delete("/{person_id}/calendar", response_model=CalendarStatus)
async def disconnect_calendar(
    person_id: str,
    user: Person = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarStatus:
    person = await _get_person_for_self_or_staff(person_id, user, db)
    person.calendar_url = None
    person.calendar_provider = None
    person.calendar_url_added_at = None
    invalidate_person_cache(person.id)
    await db.commit()
    await db.refresh(person)
    return _status(person)


@calls_router.get(
    "/{call_id}/calendar/conflicts",
    response_model=list[TaskConflictsResponse],
)
async def call_conflicts(
    call_id: str,
    user: Person = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaskConflictsResponse]:
    """Return per-task conflict info for the calling user's calendar.

    Self-only: uses the *current user's* calendar URL. If the user has
    not connected a calendar, returns an empty list (caller renders the
    "connect your calendar" tip).
    """
    if user.calendar_url is None:
        return []

    tasks_q = select(Task).where(Task.volunteer_call_id == call_id).order_by(Task.date)
    tasks_result = await db.execute(tasks_q)
    tasks = tasks_result.scalars().all()

    events = await get_events_for_person(user.id, user.calendar_url)

    out: list[TaskConflictsResponse] = []
    for t in tasks:
        if t.date is None:
            out.append(TaskConflictsResponse(task_id=t.id, has_conflict=False, conflicts=[]))
            continue
        conflicting = [e for e in events if overlaps(e, t.date, t.time_start, t.time_end)]
        out.append(
            TaskConflictsResponse(
                task_id=t.id,
                has_conflict=bool(conflicting),
                conflicts=[
                    CalendarConflict(start=e.start, end=e.end, summary=e.summary)
                    for e in conflicting
                ],
            )
        )
    return out
