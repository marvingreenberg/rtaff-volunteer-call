"""People routes."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from volunteer_call_api.database import get_db
from volunteer_call_api.models.person import (
    Person,
    PersonRole,
    Program,
    RoleType,
    Skill,
    VolunteerProgram,
)
from volunteer_call_api.routes.helpers import apply_partial_update
from volunteer_call_api.schemas.person import (
    PersonCalendarSummary,
    PersonCreate,
    PersonListResponse,
    PersonPageResponse,
    PersonResponse,
    PersonUpdate,
    ProgramMembership,
)

router = APIRouter()


def _person_roles(person: Person) -> list[RoleType]:
    return [pr.role for pr in person.roles]


def _person_programs(person: Person) -> list[ProgramMembership]:
    return [
        ProgramMembership(program=m.program, joined_at=m.joined_at, active=m.active)
        for m in person.program_memberships
    ]


def _person_response(person: Person) -> PersonResponse:
    return PersonResponse(
        id=person.id,
        first_name=person.first_name,
        last_name=person.last_name,
        email=person.email,
        phone=person.phone,
        phone_verified=person.phone_verified,
        skills=person.skills,
        active=person.active,
        notification_preference=person.notification_preference,
        notification_detail_level=person.notification_detail_level,
        subscription_status=person.subscription_status,
        pause_start=person.pause_start,
        pause_end=person.pause_end,
        notes=person.notes,
        roles=_person_roles(person),
        programs=_person_programs(person),
        calendars=[
            PersonCalendarSummary.model_validate(c, from_attributes=True) for c in person.calendars
        ],
        calendar_kind=person.calendar_kind,
        created_at=person.created_at,
        updated_at=person.updated_at,
    )


# Eager-load every relationship that _person_response touches. Forgetting
# one causes lazy-load-in-async → sqlalchemy MissingGreenlet at request
# time. Always pass these options when selecting a Person you intend to
# serialize via _person_response.
PERSON_LOAD_OPTIONS = (
    selectinload(Person.roles),
    selectinload(Person.program_memberships),
    selectinload(Person.calendars),
)


# Max rows the client can request in a single call. Prevents an
# accidental count=10000 from materializing the whole table for an
# admin search box.
MAX_PEOPLE_PAGE_SIZE = 200


@router.get("", response_model=PersonPageResponse)
async def list_people(
    role: RoleType | None = None,
    skill: Skill | None = None,
    program: Program | None = None,
    active: bool | None = None,
    search: str | None = Query(None, min_length=1),
    start: int = Query(0, ge=0),
    count: int = Query(25, ge=1, le=MAX_PEOPLE_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
) -> PersonPageResponse:
    """List people with optional filters, paginated by ``start`` / ``count``.

    Returns ``{ items, total, start, count }``. ``total`` is the
    unfiltered-by-pagination matching count (separate
    ``SELECT COUNT(DISTINCT person.id)`` against the same WHERE), so
    the frontend can render "showing N–M of TOTAL" + a filter-aware
    header label.
    """

    # Select is generic on the result-row type; the count query yields
    # tuple[int] and the items query yields tuple[Person], so we keep
    # Select as the structural type and let the row type stay loose.
    def apply_filters(q: Select[Any]) -> Select[Any]:
        if active is not None:
            q = q.where(Person.active == active)
        if skill is not None:
            # Postgres ARRAY containment via the @> operator.
            q = q.where(Person.skills.contains([skill]))
        if program is not None:
            q = q.join(Person.program_memberships).where(
                VolunteerProgram.program == program,
                VolunteerProgram.active.is_(True),
            )
        if search:
            pattern = f"%{search}%"
            full_name = func.concat(Person.first_name, " ", Person.last_name)
            q = q.where(
                or_(
                    Person.first_name.ilike(pattern),
                    Person.last_name.ilike(pattern),
                    full_name.ilike(pattern),
                )
            )
        if role is not None:
            q = q.join(Person.roles).where(PersonRole.role == role)
        return q

    # Total: separate COUNT(DISTINCT Person.id) so program/role joins
    # don't double-count people who match the filter via multiple rows
    # (e.g. a volunteer in two active programs when the program filter
    # is unset).
    count_query = apply_filters(select(func.count(func.distinct(Person.id))).select_from(Person))
    total = (await db.execute(count_query)).scalar_one()

    items_query = apply_filters(select(Person).options(*PERSON_LOAD_OPTIONS))
    # Admins know volunteers by first name — sort everywhere by first name.
    items_query = (
        items_query.order_by(Person.first_name, Person.last_name).offset(start).limit(count)
    )
    result = await db.execute(items_query)
    people = result.scalars().unique().all()

    items = [
        PersonListResponse(
            id=p.id,
            first_name=p.first_name,
            last_name=p.last_name,
            skills=p.skills,
            active=p.active,
            roles=_person_roles(p),
            programs=[m.program for m in p.program_memberships if m.active],
        )
        for p in people
    ]
    return PersonPageResponse(items=items, total=total, start=start, count=count)


@router.post("", response_model=PersonResponse, status_code=201)
async def create_person(body: PersonCreate, db: AsyncSession = Depends(get_db)) -> PersonResponse:
    """Create a new person with roles and program memberships."""
    person = Person(
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        phone=body.phone,
        skills=list(body.skills),
        active=body.active,
        notification_preference=body.notification_preference,
        notification_detail_level=body.notification_detail_level,
        subscription_status=body.subscription_status,
        notes=body.notes,
    )
    db.add(person)
    await db.flush()

    for role in body.roles:
        db.add(PersonRole(person_id=person.id, role=role))

    for program in body.programs:
        db.add(VolunteerProgram(person_id=person.id, program=program))

    await db.commit()

    result = await db.execute(
        select(Person).options(*PERSON_LOAD_OPTIONS).where(Person.id == person.id)
    )
    person = result.scalar_one()
    return _person_response(person)


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(person_id: str, db: AsyncSession = Depends(get_db)) -> PersonResponse:
    """Get a person by ID."""
    result = await db.execute(
        select(Person).options(*PERSON_LOAD_OPTIONS).where(Person.id == person_id)
    )
    person = result.scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return _person_response(person)


@router.put("/{person_id}", response_model=PersonResponse)
async def update_person(
    person_id: str, body: PersonUpdate, db: AsyncSession = Depends(get_db)
) -> PersonResponse:
    """Update a person's information, roles, and program memberships."""
    result = await db.execute(
        select(Person).options(*PERSON_LOAD_OPTIONS).where(Person.id == person_id)
    )
    person = result.scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    apply_partial_update(
        person,
        body,
        [
            "first_name",
            "last_name",
            "email",
            "phone",
            "skills",
            "active",
            "notification_preference",
            "notification_detail_level",
            "subscription_status",
            "pause_start",
            "pause_end",
            "notes",
            "calendar_kind",
        ],
    )

    if body.roles is not None:
        for pr in person.roles:
            await db.delete(pr)
        await db.flush()
        for role in body.roles:
            db.add(PersonRole(person_id=person.id, role=role))

    if body.programs is not None:
        # Full replace: drop the diff, add the diff. Preserves joined_at on
        # programs the user is keeping.
        existing = {m.program: m for m in person.program_memberships}
        new_set = set(body.programs)
        for prog, mem in list(existing.items()):
            if prog not in new_set:
                await db.delete(mem)
        await db.flush()
        for prog in new_set:
            if prog not in existing:
                db.add(VolunteerProgram(person_id=person.id, program=prog))

    await db.commit()

    result = await db.execute(
        select(Person).options(*PERSON_LOAD_OPTIONS).where(Person.id == person.id)
    )
    person = result.scalar_one()
    return _person_response(person)
