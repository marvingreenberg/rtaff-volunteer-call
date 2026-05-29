"""Tests for program-membership filtering on GET /api/volunteer-calls.

Bugs each test catches:

- ``test_volunteer_only_sees_only_their_program``: regression where
  the list endpoint returns calls from every program to a volunteer
  who only belongs to one — the original symptom that prompted the
  filter, where Vick (an RTX-only volunteer) was shown an ACR call
  alongside his own.
- ``test_staff_sees_all_programs``: regression where the program
  filter is mistakenly applied to staff/team-leader users, breaking
  the cross-program assignment dashboard.
- ``test_volunteer_with_no_active_membership_sees_nothing``: regression
  where a volunteer whose program memberships are all inactive (paused
  out of a program) still gets calls for that program.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from volunteer_call_api.database import get_db
from volunteer_call_api.dependencies import get_current_user
from volunteer_call_api.main import app
from volunteer_call_api.models import Base, Person, PersonRole
from volunteer_call_api.models.person import Program, RoleType, VolunteerProgram
from volunteer_call_api.models.volunteer_call import CallStatus, VolunteerCall


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


async def _seed_calls(db: AsyncSession) -> dict[str, str]:
    rtx = VolunteerCall(title="RTX Spring", program=Program.RTX, status=CallStatus.WAITING)
    acr = VolunteerCall(title="ACR Ramp", program=Program.ACR, status=CallStatus.WAITING)
    db.add_all([rtx, acr])
    await db.commit()
    return {"rtx": rtx.id, "acr": acr.id}


def _make_client(engine, user: Person) -> AsyncClient:
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    def _user() -> Person:
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _user
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _cleanup() -> None:
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_volunteer_only_sees_only_their_program(engine, db: AsyncSession) -> None:
    ids = await _seed_calls(db)
    vol = Person(first_name="V", last_name="One", active=True)
    vol.roles = [PersonRole(role=RoleType.VOLUNTEER)]
    vol.program_memberships = [VolunteerProgram(program=Program.RTX, active=True)]

    async with _make_client(engine, vol) as client:
        try:
            resp = await client.get("/api/volunteer-calls")
            assert resp.status_code == 200, resp.text
            returned_ids = {c["id"] for c in resp.json()}
            assert ids["rtx"] in returned_ids
            assert ids["acr"] not in returned_ids
        finally:
            _cleanup()


@pytest.mark.asyncio
async def test_staff_sees_all_programs(engine, db: AsyncSession) -> None:
    ids = await _seed_calls(db)
    staff = Person(first_name="S", last_name="Taff", active=True)
    staff.roles = [PersonRole(role=RoleType.STAFF)]
    staff.program_memberships = []

    async with _make_client(engine, staff) as client:
        try:
            resp = await client.get("/api/volunteer-calls")
            assert resp.status_code == 200, resp.text
            returned_ids = {c["id"] for c in resp.json()}
            assert ids["rtx"] in returned_ids
            assert ids["acr"] in returned_ids
        finally:
            _cleanup()


@pytest.mark.asyncio
async def test_volunteer_with_no_active_membership_sees_nothing(engine, db: AsyncSession) -> None:
    await _seed_calls(db)
    vol = Person(first_name="P", last_name="Aused", active=True)
    vol.roles = [PersonRole(role=RoleType.VOLUNTEER)]
    # The membership exists but is inactive — e.g. an unsubscribed
    # volunteer that staff haven't deleted yet.
    vol.program_memberships = [VolunteerProgram(program=Program.RTX, active=False)]

    async with _make_client(engine, vol) as client:
        try:
            resp = await client.get("/api/volunteer-calls")
            assert resp.status_code == 200, resp.text
            assert resp.json() == []
        finally:
            _cleanup()
