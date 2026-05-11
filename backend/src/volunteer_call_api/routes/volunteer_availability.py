"""Volunteer availability routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from volunteer_call_api.database import get_db
from volunteer_call_api.models.person import Person
from volunteer_call_api.models.volunteer_availability import VolunteerAvailability
from volunteer_call_api.models.volunteer_call import CallStatus, VolunteerCall
from volunteer_call_api.routes.helpers import apply_partial_update, get_one_or_404
from volunteer_call_api.schemas.volunteer_availability import (
    AvailabilityCreate,
    AvailabilityResponse,
    AvailabilityUpdate,
)

router = APIRouter()


def _availability_response(avail: VolunteerAvailability) -> AvailabilityResponse:
    person = avail.person
    name = f"{person.first_name} {person.last_name}" if person else ""
    skills = list(person.skills) if person else []
    return AvailabilityResponse(
        id=avail.id,
        volunteer_call_id=avail.volunteer_call_id,
        person_id=avail.person_id,
        person_name=name,
        person_skills=skills,
        task_id=avail.task_id,
        available=avail.available,
        max_tasks_per_week=avail.max_tasks_per_week,
        notes=avail.notes,
        created_at=avail.created_at,
        updated_at=avail.updated_at,
    )


@router.post("/{call_id}/availability", response_model=AvailabilityResponse, status_code=201)
async def submit_availability(
    call_id: str, body: AvailabilityCreate, db: AsyncSession = Depends(get_db)
) -> AvailabilityResponse:
    call = await get_one_or_404(
        db, select(VolunteerCall).where(VolunteerCall.id == call_id), "Volunteer call not found"
    )
    # Volunteers can only submit availability after invites have been sent
    # (status=WAITING) and before the admin closes assigning (assigned/archived).
    if call.status != CallStatus.WAITING:
        raise HTTPException(status_code=400, detail="Call is not open for availability")
    person_result = await db.execute(select(Person).where(Person.id == body.person_id))
    if person_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="Person not found")
    avail = VolunteerAvailability(
        volunteer_call_id=call_id,
        person_id=body.person_id,
        task_id=body.task_id,
        available=body.available,
        max_tasks_per_week=body.max_tasks_per_week,
        notes=body.notes,
    )
    db.add(avail)
    await db.commit()
    result = await db.execute(
        select(VolunteerAvailability)
        .options(selectinload(VolunteerAvailability.person))
        .where(VolunteerAvailability.id == avail.id)
    )
    avail = result.scalar_one()
    return _availability_response(avail)


@router.get("/{call_id}/availability", response_model=list[AvailabilityResponse])
async def list_availability(
    call_id: str, db: AsyncSession = Depends(get_db)
) -> list[AvailabilityResponse]:
    await get_one_or_404(
        db, select(VolunteerCall).where(VolunteerCall.id == call_id), "Volunteer call not found"
    )
    result = await db.execute(
        select(VolunteerAvailability)
        .options(selectinload(VolunteerAvailability.person))
        .where(VolunteerAvailability.volunteer_call_id == call_id)
    )
    return [_availability_response(a) for a in result.scalars().all()]


@router.put("/{call_id}/availability/{avail_id}", response_model=AvailabilityResponse)
async def update_availability(
    call_id: str,
    avail_id: str,
    body: AvailabilityUpdate,
    db: AsyncSession = Depends(get_db),
) -> AvailabilityResponse:
    result = await db.execute(
        select(VolunteerAvailability)
        .options(selectinload(VolunteerAvailability.person))
        .where(
            VolunteerAvailability.id == avail_id,
            VolunteerAvailability.volunteer_call_id == call_id,
        )
    )
    avail = result.scalar_one_or_none()
    if avail is None:
        raise HTTPException(status_code=404, detail="Availability not found")
    apply_partial_update(avail, body, ["available", "max_tasks_per_week", "notes"])
    await db.commit()
    await db.refresh(avail)
    result = await db.execute(
        select(VolunteerAvailability)
        .options(selectinload(VolunteerAvailability.person))
        .where(VolunteerAvailability.id == avail.id)
    )
    avail = result.scalar_one()
    return _availability_response(avail)


@router.delete("/{call_id}/availability/{avail_id}", status_code=204)
async def withdraw_availability(
    call_id: str, avail_id: str, db: AsyncSession = Depends(get_db)
) -> None:
    result = await db.execute(
        select(VolunteerAvailability).where(
            VolunteerAvailability.id == avail_id,
            VolunteerAvailability.volunteer_call_id == call_id,
        )
    )
    avail = result.scalar_one_or_none()
    if avail is None:
        raise HTTPException(status_code=404, detail="Availability not found")
    await db.delete(avail)
    await db.commit()
