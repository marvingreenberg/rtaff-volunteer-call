"""People routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from volunteer_call_api.database import get_db
from volunteer_call_api.models.person import Person, PersonRole, RoleType, SkillCategory
from volunteer_call_api.routes.helpers import apply_partial_update
from volunteer_call_api.schemas.person import (
    PersonCreate,
    PersonListResponse,
    PersonResponse,
    PersonUpdate,
)

router = APIRouter()


def _person_roles(person: Person) -> list[RoleType]:
    return [pr.role for pr in person.roles]


def _person_response(person: Person) -> PersonResponse:
    return PersonResponse(
        id=person.id,
        first_name=person.first_name,
        last_name=person.last_name,
        email=person.email,
        phone=person.phone,
        phone_verified=person.phone_verified,
        skill_category=person.skill_category,
        active=person.active,
        notification_preference=person.notification_preference,
        notification_detail_level=person.notification_detail_level,
        subscription_status=person.subscription_status,
        pause_start=person.pause_start,
        pause_end=person.pause_end,
        notes=person.notes,
        roles=_person_roles(person),
        created_at=person.created_at,
        updated_at=person.updated_at,
    )


@router.get("", response_model=list[PersonListResponse])
async def list_people(
    role: RoleType | None = None,
    skill_category: SkillCategory | None = None,
    active: bool | None = None,
    search: str | None = Query(None, min_length=1),
    db: AsyncSession = Depends(get_db),
) -> list[PersonListResponse]:
    """List people with optional filters."""
    query = select(Person).options(selectinload(Person.roles))

    if active is not None:
        query = query.where(Person.active == active)

    if skill_category is not None:
        query = query.where(Person.skill_category == skill_category)

    if search:
        pattern = f"%{search}%"
        full_name = func.concat(Person.first_name, " ", Person.last_name)
        query = query.where(
            or_(
                Person.first_name.ilike(pattern),
                Person.last_name.ilike(pattern),
                full_name.ilike(pattern),
            )
        )

    if role is not None:
        query = query.join(Person.roles).where(PersonRole.role == role)

    query = query.order_by(Person.last_name, Person.first_name).limit(25)
    result = await db.execute(query)
    people = result.scalars().unique().all()

    return [
        PersonListResponse(
            id=p.id,
            first_name=p.first_name,
            last_name=p.last_name,
            skill_category=p.skill_category,
            active=p.active,
            roles=_person_roles(p),
        )
        for p in people
    ]


@router.post("", response_model=PersonResponse, status_code=201)
async def create_person(body: PersonCreate, db: AsyncSession = Depends(get_db)) -> PersonResponse:
    """Create a new person with roles."""
    person = Person(
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        phone=body.phone,
        skill_category=body.skill_category,
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

    await db.commit()
    await db.refresh(person)

    result = await db.execute(
        select(Person).options(selectinload(Person.roles)).where(Person.id == person.id)
    )
    person = result.scalar_one()
    return _person_response(person)


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(person_id: str, db: AsyncSession = Depends(get_db)) -> PersonResponse:
    """Get a person by ID."""
    result = await db.execute(
        select(Person).options(selectinload(Person.roles)).where(Person.id == person_id)
    )
    person = result.scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return _person_response(person)


@router.put("/{person_id}", response_model=PersonResponse)
async def update_person(
    person_id: str, body: PersonUpdate, db: AsyncSession = Depends(get_db)
) -> PersonResponse:
    """Update a person's information and/or roles."""
    result = await db.execute(
        select(Person).options(selectinload(Person.roles)).where(Person.id == person_id)
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
            "skill_category",
            "active",
            "notification_preference",
            "notification_detail_level",
            "subscription_status",
            "pause_start",
            "pause_end",
            "notes",
        ],
    )

    if body.roles is not None:
        for pr in person.roles:
            await db.delete(pr)
        await db.flush()
        for role in body.roles:
            db.add(PersonRole(person_id=person.id, role=role))

    await db.commit()

    result = await db.execute(
        select(Person).options(selectinload(Person.roles)).where(Person.id == person.id)
    )
    person = result.scalar_one()
    return _person_response(person)
