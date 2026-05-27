"""Route-level integration tests.

These cover the previously-untested endpoints called out in the
backend-tests section of todo.md. They run against the existing
aiosqlite fixture (same pattern as test_call_list_program_filter); a
Postgres fixture for ARRAY/ENUM edge cases is still deferred and
tracked in todo.md.

Bugs each test catches are spelled out in the docstring on the test
itself.
"""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from volunteer_call_api.database import get_db
from volunteer_call_api.dependencies import get_current_user
from volunteer_call_api.main import app
from volunteer_call_api.models import Base, Person, PersonRole
from volunteer_call_api.models.person import (
    Program,
    RoleType,
    SubscriptionStatus,
    VolunteerProgram,
)
from volunteer_call_api.models.volunteer_call import CallStatus, Task, VolunteerCall

TODAY = datetime.date.today()


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

    def _stub_user() -> Person:
        staff = Person(first_name="A", last_name="Dmin", active=True)
        staff.roles = [PersonRole(role=RoleType.STAFF)]
        staff.program_memberships = []
        return staff

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _stub_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# --- send-invites state transitions ---


async def _seed_call(db: AsyncSession, status: CallStatus, program: Program = Program.RTX) -> str:
    call = VolunteerCall(title="C", program=program, status=status)
    db.add(call)
    # Add one dated task so the call is sendable.
    await db.flush()
    db.add(
        Task(
            volunteer_call_id=call.id,
            short_description="Patch",
            date=TODAY + datetime.timedelta(days=7),
            volunteers_needed=2,
        )
    )
    await db.commit()
    return call.id


@pytest.mark.asyncio
async def test_send_invites_open_to_waiting(client: AsyncClient, db: AsyncSession) -> None:
    """Bug it catches: send-invites endpoint forgets to flip status OPEN → WAITING,
    so volunteers keep seeing nothing in the list filter."""
    call_id = await _seed_call(db, CallStatus.OPEN)
    with patch(
        "volunteer_call_api.routes.volunteer_calls.deliver_notification",
        return_value=False,
    ):
        resp = await client.post(f"/api/volunteer-calls/{call_id}/send-invites")
    assert resp.status_code == 200, resp.text
    db.expire_all()
    call = await db.get(VolunteerCall, call_id)
    assert call is not None
    assert call.status == CallStatus.WAITING


@pytest.mark.asyncio
async def test_send_invites_rejects_assigned(client: AsyncClient, db: AsyncSession) -> None:
    """Bug it catches: the gate allows re-sending invites on a call that's
    already past assignment, which would surface a closed call in volunteers'
    inboxes as if it were still open."""
    call_id = await _seed_call(db, CallStatus.ASSIGNED)
    resp = await client.post(f"/api/volunteer-calls/{call_id}/send-invites")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_send_invites_rejects_archived(client: AsyncClient, db: AsyncSession) -> None:
    """Same shape as the ASSIGNED case for ARCHIVED — symmetric coverage so
    an enum addition doesn't accidentally widen the allowed set."""
    call_id = await _seed_call(db, CallStatus.ARCHIVED)
    resp = await client.post(f"/api/volunteer-calls/{call_id}/send-invites")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_send_invites_filters_by_call_program(client: AsyncClient, db: AsyncSession) -> None:
    """Bug it catches: recipient query loses the program filter and emails
    every active subscriber regardless of which program the call belongs to.
    Symptom would be ACR volunteers receiving an RTX call invite."""
    call_id = await _seed_call(db, CallStatus.OPEN, program=Program.RTX)

    rtx_vol = Person(
        first_name="R",
        last_name="TX",
        email="rtx@example.com",
        active=True,
        subscription_status=SubscriptionStatus.ACTIVE,
    )
    rtx_vol.roles = [PersonRole(role=RoleType.VOLUNTEER)]
    rtx_vol.program_memberships = [VolunteerProgram(program=Program.RTX, active=True)]

    acr_vol = Person(
        first_name="A",
        last_name="CR",
        email="acr@example.com",
        active=True,
        subscription_status=SubscriptionStatus.ACTIVE,
    )
    acr_vol.roles = [PersonRole(role=RoleType.VOLUNTEER)]
    acr_vol.program_memberships = [VolunteerProgram(program=Program.ACR, active=True)]

    db.add_all([rtx_vol, acr_vol])
    await db.commit()

    recipients: list[str] = []

    def fake_deliver(person: Person, **_kwargs: object) -> bool:
        recipients.append(person.email or "")
        return True

    with patch(
        "volunteer_call_api.routes.volunteer_calls.deliver_notification",
        side_effect=fake_deliver,
    ):
        resp = await client.post(f"/api/volunteer-calls/{call_id}/send-invites")
    assert resp.status_code == 200, resp.text
    assert "rtx@example.com" in recipients
    assert "acr@example.com" not in recipients


# --- Send assignment notices status gating ---


@pytest.mark.asyncio
async def test_send_assignment_notices_requires_assigned(
    client: AsyncClient, db: AsyncSession
) -> None:
    """Bug it catches: a regression that allows send-assignment-notices to
    fire while the call is still WAITING — volunteers get an 'assigned'
    email for a roster that hasn't been finalized."""
    call_id = await _seed_call(db, CallStatus.WAITING)
    resp = await client.post(f"/api/volunteer-calls/{call_id}/send-assignment-notices")
    assert resp.status_code == 400


# --- People / calendar leakage ---


@pytest.mark.asyncio
async def test_people_get_never_serializes_calendar_url(
    client: AsyncClient, db: AsyncSession
) -> None:
    """Bug it catches: a refactor adds calendar_url to the people response
    serializer. The URL is a bearer secret — never expose it."""
    p = Person(
        first_name="P",
        last_name="Cal",
        email="cal@example.com",
        active=True,
        calendar_url="https://calendar.example.com/secret/abc123",
        calendar_provider="google",
    )
    db.add(p)
    await db.commit()

    resp = await client.get(f"/api/people/{p.id}")
    assert resp.status_code == 200, resp.text
    body = resp.text
    assert "abc123" not in body
    assert "calendar_url" not in resp.json()
    assert resp.json()["calendar_connected"] is True


# --- DELETE call cascades ---


@pytest.mark.asyncio
async def test_delete_call_cascades_tasks(client: AsyncClient, db: AsyncSession) -> None:
    """Bug it catches: a relationship config change drops the cascade and
    deleting a call leaves orphan tasks (or trips FK constraints in
    Postgres). Aiosqlite is lenient on FKs but the row count is the
    visible signal."""
    from sqlalchemy import select

    call_id = await _seed_call(db, CallStatus.OPEN)
    tasks_before = (await db.execute(select(Task).where(Task.volunteer_call_id == call_id))).all()
    assert len(tasks_before) == 1

    resp = await client.delete(f"/api/volunteer-calls/{call_id}")
    assert resp.status_code == 204
    tasks_after = (await db.execute(select(Task).where(Task.volunteer_call_id == call_id))).all()
    assert tasks_after == []


# --- Calendar connect validates URL ---


@pytest.mark.asyncio
async def test_calendar_connect_unreachable_returns_422(
    client: AsyncClient, db: AsyncSession
) -> None:
    """Bug it catches: connect silently stores a bad URL, so the volunteer
    'has' a calendar that never produces conflicts. Surface the failure as
    a 422 instead."""
    from volunteer_call_api.services import calendar as cal_svc

    p = Person(first_name="P", last_name="Cal", email="x@example.com", active=True)
    db.add(p)
    await db.commit()

    async def stub_validate(_url: str) -> None:
        raise cal_svc.CalendarValidationError("Couldn't reach this URL. Check it and try again.")

    # connect_calendar is self-only — override the current user to match.
    def _user_p() -> Person:
        return p

    app.dependency_overrides[get_current_user] = _user_p
    with patch.object(cal_svc, "validate_calendar_url", AsyncMock(side_effect=stub_validate)):
        resp = await client.put(
            f"/api/people/{p.id}/calendar",
            json={"calendar_url": "https://no.such.host.example/cal.ics"},
        )
    assert resp.status_code == 422
    assert "couldn't reach" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_calendar_conflicts_self_only(client: AsyncClient, db: AsyncSession) -> None:
    """Bug it catches: /calendar/conflicts surfacing another user's events.
    The route is hard-coded to use the current user — calling with a
    person_id query param (or a stale path) must NOT expose someone
    else's calendar.

    Concrete check: a user with no calendar gets []; if the route
    accidentally widened to global it would return a populated list
    when other users have connected calendars.
    """
    other = Person(
        first_name="O",
        last_name="Ther",
        email="o@example.com",
        active=True,
        calendar_url="https://calendar.example.com/abc.ics",
    )
    me = Person(first_name="M", last_name="E", email="m@example.com", active=True)
    db.add_all([me, other])
    await db.commit()

    call_id = await _seed_call(db, CallStatus.WAITING)

    def _user_me() -> Person:
        return me

    app.dependency_overrides[get_current_user] = _user_me
    resp = await client.get(f"/api/volunteer-calls/{call_id}/calendar/conflicts")
    assert resp.status_code == 200, resp.text
    # me has no calendar; route must return [] regardless of who else has one.
    assert resp.json() == []
