"""Shared FastAPI dependencies."""

from fastapi import Cookie, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from volunteer_call_api.database import get_db
from volunteer_call_api.models.person import Person
from volunteer_call_api.services.tokens import TokenError, decode_token


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> Person:
    """Authenticate the request from the session cookie or a Bearer header.

    The cookie is the default for browser traffic; the header is kept as
    a fallback so server-to-server callers can authenticate without one.
    """
    token = session
    if token is None and authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        claims = decode_token(token)
    except TokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from None

    result = await db.execute(
        select(Person)
        .options(
            selectinload(Person.roles),
            # Needed by routes that scope output by program (e.g. the
            # volunteer-facing call list).
            selectinload(Person.program_memberships),
        )
        .where(Person.id == claims.person_id)
    )
    person = result.scalar_one_or_none()

    if person is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    if not person.active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    return person
