"""Shared FastAPI dependencies."""

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from volunteer_call_api.database import get_db
from volunteer_call_api.models.person import Person


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> Person:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization[7:]
    result = await db.execute(
        select(Person).options(selectinload(Person.roles)).where(Person.access_token == token)
    )
    person = result.scalar_one_or_none()

    if person is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    if not person.active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    return person
