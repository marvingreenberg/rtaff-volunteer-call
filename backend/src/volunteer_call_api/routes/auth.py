"""Auth routes for token-based volunteer identity."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from volunteer_call_api.config import settings
from volunteer_call_api.database import get_db
from volunteer_call_api.models.person import Person
from volunteer_call_api.routes.people import PERSON_LOAD_OPTIONS, _person_response
from volunteer_call_api.schemas.auth import LoginRequest, LoginResponse, VerifyRequest
from volunteer_call_api.schemas.person import PersonResponse
from volunteer_call_api.services.auth import generate_access_token
from volunteer_call_api.services.email import send_email
from volunteer_call_api.services.email_render import jinja_env
from volunteer_call_api.services.login_throttle import login_throttle
from volunteer_call_api.services.notifications import EMAIL_INLINE_IMAGES

logger = logging.getLogger(__name__)

GENERIC_LOGIN_MSG = "If {email} is registered, a login link has been sent."

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def request_magic_link(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Request a magic link for login."""
    logger.info("Magic link requested for: %s", req.email)
    result = await db.execute(select(Person).where(Person.email == req.email))
    person = result.scalar_one_or_none()
    throttled = login_throttle.is_throttled
    generic_msg = GENERIC_LOGIN_MSG.format(email=req.email)

    if person is None:
        if throttled:
            logger.info("Throttled — suppressing 404 for: %s", req.email)
            login_throttle.record_invalid()
            return LoginResponse(message=generic_msg)
        logger.warning("No person found with email: %s", req.email)
        login_throttle.record_invalid()
        raise HTTPException(status_code=404, detail="No account found for that email.")

    logger.info("Found person: %s %s (id=%s)", person.first_name, person.last_name, person.id)

    if not person.active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    if not person.access_token:
        person.access_token = generate_access_token()
        await db.commit()

    if settings.demo_mode:
        logger.warning(
            "DEMO_MODE: skipping magic-link email and returning token directly for %s",
            req.email,
        )
        return LoginResponse(
            message="Demo mode — logging in directly.", demo_token=person.access_token
        )

    template = jinja_env.get_template("magic_link_login.html")
    login_url = f"{settings.app_base_url}/verify?token={person.access_token}"
    subject = "Log in to RT-AFF"
    html_body = template.render(
        subject=subject,
        title="Log in to RT-AFF",
        subtitle="Tap the button below to sign in",
        first_name=person.first_name,
        login_url=login_url,
    )

    assert person.email is not None
    send_email(
        to=person.email,
        subject=subject,
        html_body=html_body,
        inline_images=EMAIL_INLINE_IMAGES,
    )

    if throttled:
        return LoginResponse(message=generic_msg)
    return LoginResponse(message="Magic link sent!")


@router.post("/verify", response_model=PersonResponse)
async def verify_magic_link(
    req: VerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> PersonResponse:
    """Verify a magic link token and return person info."""
    result = await db.execute(
        select(Person).options(*PERSON_LOAD_OPTIONS).where(Person.access_token == req.token)
    )
    person = result.scalar_one_or_none()

    if person is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if not person.active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    return _person_response(person)


@router.get("/me", response_model=PersonResponse)
async def get_current_user(
    token: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
) -> PersonResponse:
    """Look up a person by their access token."""
    result = await db.execute(
        select(Person).options(*PERSON_LOAD_OPTIONS).where(Person.access_token == token)
    )
    person = result.scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if not person.active:
        raise HTTPException(status_code=403, detail="Account is inactive")
    return _person_response(person)
