"""Tests for pause-date enforcement on availability submission.

Bugs each test catches:

- ``test_paused_volunteer_blocked_in_window``: regression where a
  volunteer with status=PAUSED and today in [pause_start, pause_end]
  can still POST availability — they shouldn't because notifications
  to them are suppressed, so any "yes I'm available" reply they
  submit out-of-band would be ignored anyway.
- ``test_active_volunteer_unaffected``: regression where the pause
  check accidentally rejects ACTIVE volunteers (e.g. wrong status
  comparison, or pause window applied unconditionally).
- ``test_paused_volunteer_outside_window_allowed``: regression where
  a volunteer marked PAUSED but with the window ending in the past
  (i.e. the pause already expired but the status wasn't reset) is
  treated as still paused — overly strict.
"""

from __future__ import annotations

import datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from volunteer_call_api.database import get_db
from volunteer_call_api.dependencies import get_current_user
from volunteer_call_api.main import app
from volunteer_call_api.models import Base, Person
from volunteer_call_api.models.person import Program, SubscriptionStatus
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


@pytest.fixture
async def client(engine) -> AsyncClient:
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    def _stub_user() -> Person:
        return Person(first_name="A", last_name="Dmin", active=True)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _stub_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _seed_call(db: AsyncSession) -> VolunteerCall:
    call = VolunteerCall(title="C", program=Program.RTX, status=CallStatus.WAITING)
    db.add(call)
    await db.commit()
    return call


TODAY = datetime.date.today()


@pytest.mark.asyncio
async def test_paused_volunteer_blocked_in_window(client: AsyncClient, db: AsyncSession) -> None:
    call = await _seed_call(db)
    p = Person(
        first_name="P",
        last_name="Aused",
        active=True,
        subscription_status=SubscriptionStatus.PAUSED,
        pause_start=TODAY - datetime.timedelta(days=1),
        pause_end=TODAY + datetime.timedelta(days=7),
    )
    db.add(p)
    await db.commit()

    resp = await client.post(
        f"/api/volunteer-calls/{call.id}/availability",
        json={"person_id": p.id, "available": True},
    )
    assert resp.status_code == 400
    assert "paused" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_active_volunteer_unaffected(client: AsyncClient, db: AsyncSession) -> None:
    call = await _seed_call(db)
    p = Person(
        first_name="A",
        last_name="Ctive",
        active=True,
        subscription_status=SubscriptionStatus.ACTIVE,
    )
    db.add(p)
    await db.commit()

    resp = await client.post(
        f"/api/volunteer-calls/{call.id}/availability",
        json={"person_id": p.id, "available": True},
    )
    assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_paused_volunteer_outside_window_allowed(
    client: AsyncClient, db: AsyncSession
) -> None:
    call = await _seed_call(db)
    p = Person(
        first_name="E",
        last_name="Xpired",
        active=True,
        subscription_status=SubscriptionStatus.PAUSED,
        pause_start=TODAY - datetime.timedelta(days=30),
        pause_end=TODAY - datetime.timedelta(days=1),
    )
    db.add(p)
    await db.commit()

    resp = await client.post(
        f"/api/volunteer-calls/{call.id}/availability",
        json={"person_id": p.id, "available": True},
    )
    assert resp.status_code == 201, resp.text
