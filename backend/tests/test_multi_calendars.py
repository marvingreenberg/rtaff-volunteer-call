"""Tests for the multi-calendar collection routes + union conflict logic.

Bugs each test catches:

- ``test_add_calendar_appends_to_collection``: regression where POST
  /people/{id}/calendars overwrites an existing row instead of
  appending, defeating the whole purpose of the multi-calendar
  change.
- ``test_delete_calendar_removes_specific_row``: regression where
  DELETE wipes all calendars instead of the targeted one.
- ``test_conflicts_union_across_two_calendars``: regression where
  the conflict route only looks at the first calendar — symptom is a
  user with personal + work feeds only ever conflicting on personal.
- ``test_listing_never_returns_calendar_url``: belt-and-suspenders
  for the bearer-secret invariant on the new collection endpoint.
"""

from __future__ import annotations

import datetime as dt
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from volunteer_call_api.database import get_db
from volunteer_call_api.dependencies import get_current_user
from volunteer_call_api.main import app
from volunteer_call_api.models import Base, Person, PersonCalendar
from volunteer_call_api.models.person import Program
from volunteer_call_api.models.volunteer_call import CallStatus, Task, VolunteerCall
from volunteer_call_api.services import calendar as cal_svc


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
async def client(engine, db) -> AsyncClient:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    p = Person(first_name="A", last_name="B", email="a@example.com", active=True)
    db.add(p)
    await db.commit()

    async def override_get_db():
        async with factory() as session:
            yield session

    def _user() -> Person:
        return p

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac._user_id = p.id  # type: ignore[attr-defined]
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_add_calendar_appends_to_collection(client: AsyncClient, db: AsyncSession) -> None:
    person_id = client._user_id  # type: ignore[attr-defined]
    with patch(
        "volunteer_call_api.routes.calendar.validate_calendar_url",
        AsyncMock(return_value=None),
    ):
        r1 = await client.post(
            f"/api/people/{person_id}/calendars",
            json={
                "calendar_url": "https://cal.example/a.ics",
                "calendar_provider": "google",
                "label": "Personal",
            },
        )
        r2 = await client.post(
            f"/api/people/{person_id}/calendars",
            json={
                "calendar_url": "https://cal.example/b.ics",
                "calendar_provider": "outlook",
                "label": "Work",
            },
        )
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text
    listing = await client.get(f"/api/people/{person_id}/calendars")
    assert listing.status_code == 200
    rows = listing.json()
    assert len(rows) == 2
    labels = sorted(r["label"] for r in rows)
    assert labels == ["Personal", "Work"]


@pytest.mark.asyncio
async def test_delete_calendar_removes_specific_row(client: AsyncClient, db: AsyncSession) -> None:
    person_id = client._user_id  # type: ignore[attr-defined]
    with patch(
        "volunteer_call_api.routes.calendar.validate_calendar_url",
        AsyncMock(return_value=None),
    ):
        await client.post(
            f"/api/people/{person_id}/calendars",
            json={"calendar_url": "https://cal.example/a.ics", "label": "Personal"},
        )
        r2 = await client.post(
            f"/api/people/{person_id}/calendars",
            json={"calendar_url": "https://cal.example/b.ics", "label": "Work"},
        )
    work_id = r2.json()["id"]

    del_resp = await client.delete(f"/api/people/{person_id}/calendars/{work_id}")
    assert del_resp.status_code == 204

    rows = (await client.get(f"/api/people/{person_id}/calendars")).json()
    assert len(rows) == 1
    assert rows[0]["label"] == "Personal"


@pytest.mark.asyncio
async def test_listing_never_returns_calendar_url(client: AsyncClient, db: AsyncSession) -> None:
    person_id = client._user_id  # type: ignore[attr-defined]
    with patch(
        "volunteer_call_api.routes.calendar.validate_calendar_url",
        AsyncMock(return_value=None),
    ):
        await client.post(
            f"/api/people/{person_id}/calendars",
            json={
                "calendar_url": "https://cal.example/secret123.ics",
                "label": "Personal",
            },
        )
    rows = (await client.get(f"/api/people/{person_id}/calendars")).text
    assert "secret123" not in rows
    assert "calendar_url" not in rows


@pytest.mark.asyncio
async def test_conflicts_union_across_two_calendars(client: AsyncClient, db: AsyncSession) -> None:
    """Two connected calendars; first has an event on day-A, second on
    day-B. A call with tasks on both days must surface BOTH as
    conflicts."""
    person_id = client._user_id  # type: ignore[attr-defined]
    cal_svc._cache.clear()

    db.add_all(
        [
            PersonCalendar(
                person_id=person_id,
                calendar_url="https://cal.example/personal.ics",
                label="Personal",
            ),
            PersonCalendar(
                person_id=person_id,
                calendar_url="https://cal.example/work.ics",
                label="Work",
            ),
        ]
    )
    call = VolunteerCall(title="C", program=Program.RTX, status=CallStatus.WAITING)
    db.add(call)
    await db.flush()
    day_a = dt.date.today() + dt.timedelta(days=7)
    day_b = dt.date.today() + dt.timedelta(days=8)
    db.add_all(
        [
            Task(volunteer_call_id=call.id, short_description="T1", date=day_a),
            Task(volunteer_call_id=call.id, short_description="T2", date=day_b),
        ]
    )
    await db.commit()

    personal_event = cal_svc.CalendarEvent(
        start=dt.datetime.combine(day_a, dt.time(9, 0), tzinfo=dt.timezone.utc),
        end=dt.datetime.combine(day_a, dt.time(10, 0), tzinfo=dt.timezone.utc),
        summary="Personal appointment",
        is_all_day=False,
    )
    work_event = cal_svc.CalendarEvent(
        start=dt.datetime.combine(day_b, dt.time(9, 0), tzinfo=dt.timezone.utc),
        end=dt.datetime.combine(day_b, dt.time(10, 0), tzinfo=dt.timezone.utc),
        summary="Work meeting",
        is_all_day=False,
    )

    async def fake_fetch(
        url: str,
        _window: object = None,
    ) -> list[cal_svc.CalendarEvent]:
        return [personal_event] if "personal" in url else [work_event]

    with patch.object(cal_svc, "fetch_and_parse", side_effect=fake_fetch):
        resp = await client.get(f"/api/volunteer-calls/{call.id}/calendar/conflicts")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    flagged = {r["task_id"]: r for r in body if r["has_conflict"]}
    assert len(flagged) == 2
    summaries = sorted(c["summary"] for r in body for c in r["conflicts"])
    assert summaries == ["Personal appointment", "Work meeting"]
