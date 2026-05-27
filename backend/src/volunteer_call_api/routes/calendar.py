"""Calendar URL connection + per-call conflict computation.

A user can connect multiple iCal feeds (e.g. personal + work); each
URL is treated as a bearer secret and never returned by the API. The
collection routes (GET/POST/DELETE under
``/people/{id}/calendars``) are self-only (or staff acting on
another user's profile). The conflicts endpoint is self-only and
unions events from every connected feed.
"""

from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from volunteer_call_api.database import get_db
from volunteer_call_api.dependencies import get_current_user
from volunteer_call_api.models.person import Person, PersonCalendar, RoleType
from volunteer_call_api.models.volunteer_call import Task
from volunteer_call_api.schemas.person import (
    CalendarConflict,
    CalendarConnect,
    PersonCalendarSummary,
    TaskConflictsResponse,
)
from volunteer_call_api.services.calendar import (
    CalendarValidationError,
    get_events_for_person,
    invalidate_person_cache,
    overlaps,
    validate_calendar_url,
)

# Mounted at /api/people; handles per-person collection of calendars.
people_router = APIRouter()
# Mounted at /api/volunteer-calls; handles per-call conflict lookup.
calls_router = APIRouter()


def _is_staff(user: Person) -> bool:
    return any(r.role == RoleType.STAFF for r in user.roles)


async def _get_person_for_self_or_staff(person_id: str, user: Person, db: AsyncSession) -> Person:
    if person_id != user.id and not _is_staff(user):
        raise HTTPException(status_code=403, detail="Forbidden")
    result = await db.execute(
        select(Person)
        .options(selectinload(Person.roles), selectinload(Person.calendars))
        .where(Person.id == person_id)
    )
    person = result.scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


def _summary(cal: PersonCalendar) -> PersonCalendarSummary:
    return PersonCalendarSummary.model_validate(cal, from_attributes=True)


@people_router.get(
    "/{person_id}/calendars",
    response_model=list[PersonCalendarSummary],
)
async def list_calendars(
    person_id: str,
    user: Person = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PersonCalendarSummary]:
    person = await _get_person_for_self_or_staff(person_id, user, db)
    return [_summary(c) for c in person.calendars]


@people_router.post(
    "/{person_id}/calendars",
    response_model=PersonCalendarSummary,
    status_code=201,
)
async def add_calendar(
    person_id: str,
    body: CalendarConnect,
    user: Person = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PersonCalendarSummary:
    """Connect another iCal feed. Conflict detection unions events
    across every feed on the person."""
    person = await _get_person_for_self_or_staff(person_id, user, db)
    try:
        await validate_calendar_url(body.calendar_url)
    except CalendarValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    cal = PersonCalendar(
        person_id=person.id,
        calendar_url=body.calendar_url,
        calendar_provider=body.calendar_provider,
        label=body.label,
    )
    db.add(cal)
    invalidate_person_cache(person.id)
    await db.commit()
    await db.refresh(cal)
    return _summary(cal)


@people_router.delete("/{person_id}/calendars/{calendar_id}", status_code=204)
async def remove_calendar(
    person_id: str,
    calendar_id: str,
    user: Person = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    person = await _get_person_for_self_or_staff(person_id, user, db)
    target = next((c for c in person.calendars if c.id == calendar_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Calendar not found")
    await db.delete(target)
    invalidate_person_cache(person.id)
    await db.commit()


@calls_router.get(
    "/{call_id}/calendar/conflicts",
    response_model=list[TaskConflictsResponse],
)
async def call_conflicts(
    call_id: str,
    user: Person = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaskConflictsResponse]:
    """Return per-task conflict info, unioning events from every
    calendar the calling user has connected.

    Self-only: uses the *current user's* calendar list. Empty list out
    when no calendars are connected — caller renders the "connect your
    calendar" tip.
    """
    # Reload the user with calendars eager-loaded — get_current_user
    # already loads them, but a defensive refetch keeps this route
    # honest if that dependency changes.
    result = await db.execute(
        select(Person).options(selectinload(Person.calendars)).where(Person.id == user.id)
    )
    me = result.scalar_one()
    if not me.calendars:
        return []

    tasks_q = select(Task).where(Task.volunteer_call_id == call_id).order_by(Task.date)
    tasks_result = await db.execute(tasks_q)
    tasks = tasks_result.scalars().all()

    # Window for recurrence expansion: bounded by the call's task dates
    # with a one-day buffer either side. Falls back to no window when
    # the call has no dated tasks (the per-task overlap loop below
    # yields no conflicts anyway).
    dated = [t.date for t in tasks if t.date is not None]
    if dated:
        start = datetime.combine(min(dated) - timedelta(days=1), time(0, 0), tzinfo=timezone.utc)
        end = datetime.combine(max(dated) + timedelta(days=1), time(23, 59), tzinfo=timezone.utc)
        window: tuple[datetime, datetime] | None = (start, end)
    else:
        window = None

    # Union events across every connected feed. Each fetch is cached
    # per (person, url, window) so calling repeatedly across calls is
    # cheap.
    events = []
    for cal in me.calendars:
        events.extend(await get_events_for_person(me.id, cal.calendar_url, window))

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
