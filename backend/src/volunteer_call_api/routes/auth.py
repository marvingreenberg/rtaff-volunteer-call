"""Auth routes — JWT-based magic-link login + cookie session."""

import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from volunteer_call_api.config import settings
from volunteer_call_api.database import get_db
from volunteer_call_api.models.person import Person, PersonLoginAlias
from volunteer_call_api.routes.people import PERSON_LOAD_OPTIONS, _person_response
from volunteer_call_api.schemas.auth import (
    LoginRequest,
    LoginResponse,
    VerifyRequest,
    VerifyResponse,
)
from volunteer_call_api.schemas.person import PersonResponse
from volunteer_call_api.services.email import send_email
from volunteer_call_api.services.email_render import jinja_env
from volunteer_call_api.services.login_throttle import login_throttle
from volunteer_call_api.services.notifications import EMAIL_INLINE_IMAGES
from volunteer_call_api.services.tokens import (
    TokenError,
    decode_token,
    issue_login_token,
    issue_session_token,
)

logger = logging.getLogger(__name__)

GENERIC_LOGIN_MSG = "If {email} is registered, a login link has been sent."

# Name of the HttpOnly session cookie set on /verify.
SESSION_COOKIE = "session"
# Cookie lifetime mirrors the session-token TTL — clients won't carry a
# longer cookie than the token inside it is valid.
SESSION_COOKIE_MAX_AGE = 60 * 60 * 24 * settings.jwt_session_ttl_days

router = APIRouter()


def _set_session_cookie(request: Request, response: Response, person_id: str) -> None:
    """Mint a fresh session token for ``person_id`` and set it as an HttpOnly cookie.

    The session token is minted here rather than reusing the inbound
    magic-link/invite token: those are short-lived (a login link lives
    ~10 minutes), but the session should last ``jwt_session_ttl_days``.
    Storing the link token would expire the session with the link.

    SameSite=Lax is enough to block cross-site POST CSRF on cookie-only
    auth; a follow-up should add explicit CSRF tokens before any
    state-changing public form lands. ``secure`` follows the request
    scheme so dev (http://localhost) works and production (https) is
    correctly hardened.
    """
    response.set_cookie(
        key=SESSION_COOKIE,
        value=issue_session_token(person_id),
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        path="/",
    )


@router.post("/login", response_model=LoginResponse)
async def request_magic_link(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Request a magic-link email. Mints a login JWT."""
    logger.info("Magic link requested for: %s", req.email)
    lookup_email = req.email.strip().lower()
    result = await db.execute(select(Person).where(func.lower(Person.email) == lookup_email))
    person = result.scalar_one_or_none()
    if person is None:
        alias_result = await db.execute(
            select(Person)
            .join(PersonLoginAlias, PersonLoginAlias.person_id == Person.id)
            .where(PersonLoginAlias.email == lookup_email)
        )
        person = alias_result.scalar_one_or_none()
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

    token = issue_login_token(person.id)

    if settings.demo_mode:
        logger.warning(
            "DEMO_MODE: skipping magic-link email and returning token directly for %s",
            req.email,
        )
        return LoginResponse(message="Demo mode — logging in directly.", demo_token=token)

    template = jinja_env.get_template("magic_link_login.html")
    login_url = f"{settings.app_base_url}/verify?token={token}"
    subject = "Log in to RT-AFF"
    html_body = template.render(
        subject=subject,
        title="Log in to RT-AFF",
        subtitle="Tap the button below to sign in",
        first_name=person.first_name,
        login_url=login_url,
    )

    send_email(
        to=req.email,
        subject=subject,
        html_body=html_body,
        inline_images=EMAIL_INLINE_IMAGES,
    )

    if throttled:
        return LoginResponse(message=generic_msg)
    return LoginResponse(message="Magic link sent!")


async def _person_by_token(token: str, db: AsyncSession) -> tuple[Person, str | None]:
    """Decode a session/invite JWT and load the person. Returns (person, call_id)."""
    try:
        claims = decode_token(token)
    except TokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from None

    result = await db.execute(
        select(Person).options(*PERSON_LOAD_OPTIONS).where(Person.id == claims.person_id)
    )
    person = result.scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if not person.active:
        raise HTTPException(status_code=403, detail="Account is inactive")
    return person, claims.call_id


@router.post("/verify", response_model=VerifyResponse)
async def verify_magic_link(
    req: VerifyRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> VerifyResponse:
    """Verify a magic-link/invite JWT, set the session cookie, return person + call context."""
    person, call_id = await _person_by_token(req.token, db)
    _set_session_cookie(request, response, person.id)
    return VerifyResponse(person=_person_response(person), invited_call_id=call_id)


@router.get("/me", response_model=PersonResponse)
async def get_me(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    token: str | None = Query(default=None, min_length=1),
    session: str | None = Cookie(default=None),
) -> PersonResponse:
    """Return the current user.

    A *valid* ``?token=`` from a freshly clicked email link takes
    precedence over an existing session cookie, so a new link always wins
    (switching accounts, re-authenticating). When the URL token is used we
    (re)mint the session cookie for that person, upgrading the short-lived
    link into a normal-length session and dropping the need to carry the
    URL credential on later requests.

    An invalid or expired URL token does *not* clobber an existing
    session — we fall back to the cookie rather than 401, so clicking a
    stale link while already signed in doesn't sign you out.
    """
    if token is not None:
        try:
            decode_token(token)
        except TokenError:
            token = None  # fall through to the session cookie

    if token is not None:
        person, _ = await _person_by_token(token, db)
        _set_session_cookie(request, response, person.id)
        return _person_response(person)

    if session is not None:
        person, _ = await _person_by_token(session, db)
        return _person_response(person)

    raise HTTPException(status_code=401, detail="Not authenticated")


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    """Clear the session cookie."""
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"message": "Logged out"}
