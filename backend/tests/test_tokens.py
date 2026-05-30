"""Tests for the JWT token service and the cookie-session flow.

Bugs each test catches:

- ``test_login_token_round_trip``: regression where ``decode_token``
  drops the ``typ`` claim and silently treats login tokens as invite
  tokens (or vice versa), breaking the deep-link logic.
- ``test_invite_token_carries_call_id``: regression where the invite
  builder forgets the ``call_id`` claim, so the frontend can't deep-link.
- ``test_expired_token_raises_token_expired``: regression where the
  decoder swallows ``jwt.ExpiredSignatureError`` and returns a generic
  ``TokenInvalid``, defeating the "expired vs malformed" distinction.
- ``test_tampered_signature_raises_token_invalid``: regression where the
  signing key check is bypassed (e.g. ``algorithms=["none"]``).
- ``test_invite_token_without_call_id_rejected``: regression where an
  ``invite`` typ token without a ``call_id`` is accepted, letting a
  caller mint a privileged shape with claims-only context.
- ``test_me_endpoint_uses_cookie_when_no_query_token``: regression where
  ``/auth/me`` only reads the ``?token=`` query param and ignores the
  session cookie set by ``/auth/verify``.
- ``test_verify_returns_invited_call_id_for_invite_token``: regression
  where invite tokens are accepted but the call id is dropped from the
  response, so the frontend can't auto-scroll to the right call.
- ``test_availability_submit_allowed_when_assigned``: regression where
  the volunteer-availability submit gate rejects standby submissions on
  ASSIGNED calls (which is the whole point of the call-status banner UX).
- ``test_availability_submit_rejected_when_archived``: regression where
  the same gate accepts submissions on ARCHIVED calls.
"""

from __future__ import annotations

from datetime import timedelta

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from volunteer_call_api.config import settings
from volunteer_call_api.database import get_db
from volunteer_call_api.main import app
from volunteer_call_api.models import Base, Person
from volunteer_call_api.models.volunteer_call import CallStatus, VolunteerCall
from volunteer_call_api.services.login_throttle import login_throttle
from volunteer_call_api.services.tokens import (
    TokenExpired,
    TokenInvalid,
    decode_token,
    issue_invite_token,
    issue_login_token,
    issue_session_token,
)

# Tolerance (seconds) when asserting a token's lifetime — covers the few
# milliseconds between minting and decoding inside a test.
TTL_TOLERANCE_SECONDS = 5

# --- Unit tests for the token service ---


def test_login_token_round_trip() -> None:
    token = issue_login_token("person-1")
    claims = decode_token(token)
    assert claims.person_id == "person-1"
    assert claims.token_type == "login"
    assert claims.call_id is None


def test_invite_token_carries_call_id() -> None:
    token = issue_invite_token("person-1", "call-7")
    claims = decode_token(token)
    assert claims.token_type == "invite"
    assert claims.call_id == "call-7"


def _ttl_seconds(token: str) -> float:
    claims = decode_token(token)
    return (claims.expires_at - claims.issued_at).total_seconds()


def test_login_token_default_ttl_is_short() -> None:
    """Login magic links must be short-lived (~jwt_login_ttl_minutes).

    Catches a regression that leaves login links on the old 14-day TTL,
    defeating the whole point of the short magic-link window.
    """
    expected = settings.jwt_login_ttl_minutes * 60
    assert abs(_ttl_seconds(issue_login_token("p")) - expected) < TTL_TOLERANCE_SECONDS


def test_invite_token_default_ttl_is_long() -> None:
    """Invite links keep a multi-day TTL — recipients click days later.

    Catches accidentally applying the 10-minute login window to invites.
    """
    expected = settings.jwt_invite_ttl_days * 24 * 60 * 60
    assert abs(_ttl_seconds(issue_invite_token("p", "c")) - expected) < TTL_TOLERANCE_SECONDS


def test_session_token_round_trip_and_ttl() -> None:
    """Session tokens decode with typ=session and the session TTL.

    Catches forgetting ``"session"`` in ``decode_token``'s allow-list, and
    a regression that mints the session with a link-length TTL.
    """
    token = issue_session_token("person-1")
    claims = decode_token(token)
    assert claims.token_type == "session"
    assert claims.call_id is None
    expected = settings.jwt_session_ttl_days * 24 * 60 * 60
    assert abs(_ttl_seconds(token) - expected) < TTL_TOLERANCE_SECONDS


def test_expired_token_raises_token_expired() -> None:
    token = issue_login_token("person-1", ttl=timedelta(seconds=-1))
    with pytest.raises(TokenExpired):
        decode_token(token)


def test_tampered_signature_raises_token_invalid() -> None:
    token = issue_login_token("person-1")
    tampered = token[:-4] + "AAAA"
    with pytest.raises(TokenInvalid):
        decode_token(tampered)


def test_invite_token_without_call_id_rejected() -> None:
    """A hand-crafted invite-typ token missing call_id must be rejected."""
    payload = {"sub": "person-1", "typ": "invite"}
    forged = pyjwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    with pytest.raises(TokenInvalid):
        decode_token(forged)


# --- Integration tests for the cookie-session flow ---


@pytest.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def db(engine) -> AsyncSession:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def client(engine) -> AsyncClient:
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    login_throttle._reset()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    login_throttle._reset()


async def _seed_person(db: AsyncSession, email: str = "u@example.com") -> Person:
    person = Person(first_name="U", last_name="Ser", email=email, active=True)
    db.add(person)
    await db.commit()
    return person


async def _seed_call(db: AsyncSession, status: CallStatus = CallStatus.WAITING) -> VolunteerCall:
    from volunteer_call_api.models.person import Program

    call = VolunteerCall(title="Spring Call", program=Program.RTX, status=status)
    db.add(call)
    await db.commit()
    return call


@pytest.mark.asyncio
async def test_me_endpoint_uses_cookie_when_no_query_token(
    client: AsyncClient, db: AsyncSession
) -> None:
    person = await _seed_person(db)
    token = issue_login_token(person.id)

    # First, /verify sets the cookie on the client.
    verify_resp = await client.post("/api/auth/verify", json={"token": token})
    assert verify_resp.status_code == 200

    # Subsequent /me request carries only the cookie — no ?token=.
    me_resp = await client.get("/api/auth/me")
    assert me_resp.status_code == 200, me_resp.text
    assert me_resp.json()["id"] == person.id


@pytest.mark.asyncio
async def test_verify_sets_session_token_cookie_not_the_link_token(
    client: AsyncClient, db: AsyncSession
) -> None:
    """The cookie set by /verify is a long-lived *session* token, not the
    short login token that was clicked.

    Catches a regression to storing the inbound magic-link token in the
    cookie: with the 10-minute login TTL that would log the user out
    minutes after login.
    """
    person = await _seed_person(db)
    login_token = issue_login_token(person.id)
    resp = await client.post("/api/auth/verify", json={"token": login_token})
    assert resp.status_code == 200, resp.text

    cookie_value = client.cookies.get("session")
    assert cookie_value is not None
    assert cookie_value != login_token
    claims = decode_token(cookie_value)
    assert claims.token_type == "session"
    expected = settings.jwt_session_ttl_days * 24 * 60 * 60
    assert (
        claims.expires_at - claims.issued_at
    ).total_seconds() > settings.jwt_login_ttl_minutes * 60
    assert (
        abs((claims.expires_at - claims.issued_at).total_seconds() - expected)
        < TTL_TOLERANCE_SECONDS
    )


@pytest.mark.asyncio
async def test_me_url_token_overrides_session_cookie(client: AsyncClient, db: AsyncSession) -> None:
    """An explicit ?token= wins over an existing session cookie, and the
    cookie is re-minted for that person.

    Catches the ``session or token`` precedence bug where a stale cookie
    masks a freshly clicked link (and the failure to switch the session
    to the new person).
    """
    person_a = await _seed_person(db, email="a@example.com")
    person_b = await _seed_person(db, email="b@example.com")

    # Establish a session as A.
    await client.post("/api/auth/verify", json={"token": issue_login_token(person_a.id)})

    # Land on a link for B while A's cookie is still present.
    me_resp = await client.get(f"/api/auth/me?token={issue_login_token(person_b.id)}")
    assert me_resp.status_code == 200, me_resp.text
    assert me_resp.json()["id"] == person_b.id

    # The cookie should now resolve to B without any URL token.
    follow_up = await client.get("/api/auth/me")
    assert follow_up.status_code == 200, follow_up.text
    assert follow_up.json()["id"] == person_b.id


@pytest.mark.asyncio
async def test_me_stale_url_token_falls_back_to_session(
    client: AsyncClient, db: AsyncSession
) -> None:
    """An expired/invalid ?token= does not sign out an existing session.

    Catches a regression where preferring the URL token unconditionally
    401s a signed-in user who clicks a stale link.
    """
    person = await _seed_person(db)
    await client.post("/api/auth/verify", json={"token": issue_login_token(person.id)})

    expired = issue_login_token(person.id, ttl=timedelta(seconds=-1))
    resp = await client.get(f"/api/auth/me?token={expired}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == person.id


@pytest.mark.asyncio
async def test_verify_rejects_expired_login_token(client: AsyncClient, db: AsyncSession) -> None:
    """A login link clicked after its TTL is rejected at /verify.

    Catches expiry not being enforced on the verify path.
    """
    person = await _seed_person(db)
    stale = issue_login_token(person.id, ttl=timedelta(seconds=-1))
    resp = await client.post("/api/auth/verify", json={"token": stale})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint_401_without_cookie_or_token(client: AsyncClient) -> None:
    # No prior /verify call → no cookie → /me is unauthenticated.
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_verify_returns_invited_call_id_for_invite_token(
    client: AsyncClient, db: AsyncSession
) -> None:
    person = await _seed_person(db)
    call = await _seed_call(db)
    token = issue_invite_token(person.id, call.id)

    resp = await client.post("/api/auth/verify", json={"token": token})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["invited_call_id"] == call.id
    assert body["person"]["id"] == person.id


async def _authenticate(client: AsyncClient, person: Person) -> None:
    """Bootstrap the session cookie on the test client."""
    token = issue_login_token(person.id)
    resp = await client.post("/api/auth/verify", json={"token": token})
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_availability_submit_allowed_when_assigned(
    client: AsyncClient, db: AsyncSession
) -> None:
    person = await _seed_person(db)
    call = await _seed_call(db, status=CallStatus.ASSIGNED)
    await _authenticate(client, person)
    resp = await client.post(
        f"/api/volunteer-calls/{call.id}/availability",
        json={"person_id": person.id, "available": True},
    )
    assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_availability_submit_rejected_when_archived(
    client: AsyncClient, db: AsyncSession
) -> None:
    person = await _seed_person(db)
    call = await _seed_call(db, status=CallStatus.ARCHIVED)
    await _authenticate(client, person)
    resp = await client.post(
        f"/api/volunteer-calls/{call.id}/availability",
        json={"person_id": person.id, "available": True},
    )
    assert resp.status_code == 400
