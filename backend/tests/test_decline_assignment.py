"""Tests for the volunteer self-decline endpoint."""

from __future__ import annotations

import datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from volunteer_call_api.database import get_db
from volunteer_call_api.dependencies import get_current_user
from volunteer_call_api.main import app
from volunteer_call_api.models import Base, Person
from volunteer_call_api.models.person import Program
from volunteer_call_api.models.team_assignment import AssignmentRole, TeamAssignment
from volunteer_call_api.models.volunteer_call import CallStatus, Task, VolunteerCall
from volunteer_call_api.services import notifications

TODAY = datetime.date.today()
JOB_DATE = TODAY + datetime.timedelta(days=7)


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


class Recorder:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []  # (email, subject, full_body)

    def __call__(self, *, person, subject, full_body, summary_body, **kwargs) -> bool:
        self.sent.append((person.email or "", subject, full_body))
        return True

    def to(self, email: str) -> list[tuple[str, str, str]]:
        return [s for s in self.sent if s[0] == email]

    @property
    def recipients(self) -> set[str]:
        return {s[0] for s in self.sent}


def _client(engine, acting_user_id: str) -> AsyncClient:
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    def _user() -> Person:
        return Person(id=acting_user_id, first_name="Acting", last_name="User", active=True)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _user
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _seed(db: AsyncSession, *, status: CallStatus = CallStatus.ASSIGNED):
    admin = Person(first_name="Ada", last_name="Admin", email="admin@example.com")
    lead = Person(first_name="Lee", last_name="Lead", email="lead@example.com")
    vol = Person(first_name="Vic", last_name="Volunteer", email="vol@example.com")
    other = Person(first_name="Ona", last_name="Other", email="other@example.com")
    db.add_all([admin, lead, vol, other])
    await db.flush()
    call = VolunteerCall(
        title="June Repair", program=Program.RTX, status=status, created_by_id=admin.id
    )
    db.add(call)
    await db.flush()
    task = Task(
        volunteer_call_id=call.id,
        short_description="Replace ceiling fan",
        date=JOB_DATE,
        address="500 Oak Ave",
        city="Arlington",
        volunteers_needed=4,
        team_lead_id=lead.id,
    )
    db.add(task)
    await db.flush()
    vol_assignment = TeamAssignment(
        task_id=task.id, person_id=vol.id, role=AssignmentRole.VOLUNTEER
    )
    db.add(vol_assignment)
    db.add(TeamAssignment(task_id=task.id, person_id=other.id, role=AssignmentRole.VOLUNTEER))
    await db.flush()
    # Pretend a prior send happened so we can assert the snapshot is trimmed.
    call.last_sent_roster = {
        task.id: {"assigned": sorted([vol.id, other.id]), "team_lead": lead.id}
    }
    await db.commit()
    return {
        "admin": admin,
        "lead": lead,
        "vol": vol,
        "other": other,
        "call": call,
        "task": task,
        "vol_assignment": vol_assignment,
    }


@pytest.mark.asyncio
async def test_owner_decline_deletes_assignment_and_notifies_lead_and_admin(
    engine, db: AsyncSession
) -> None:
    """Declining must hard-delete the assignment, notify the lead and admin with
    the volunteer's message, send the volunteer a brief ack, and trim the
    snapshot so the next batch send doesn't re-fire a removal email. Catches a
    no-op decline, a missing notification, a dropped message, and the
    double-email-on-next-send bug."""
    s = await _seed(db)
    vol_id = s["vol"].id
    task_id = s["task"].id
    call_id = s["call"].id
    assignment_id = s["vol_assignment"].id

    orig = notifications.deliver_notification
    rec = Recorder()
    notifications.deliver_notification = rec  # type: ignore[assignment]
    try:
        async with _client(engine, vol_id) as client:
            resp = await client.post(
                f"/api/volunteering/my-assignments/{assignment_id}/decline",
                json={"message": "Sorry Lee, cannot make it that day."},
            )
    finally:
        app.dependency_overrides.clear()
        notifications.deliver_notification = orig  # type: ignore[assignment]

    assert resp.status_code == 200

    # Verify persisted state from a fresh session (the seeding session caches
    # its own stale instances).
    verify = async_sessionmaker(engine, expire_on_commit=False)
    async with verify() as vs:
        remaining = (
            await vs.execute(select(TeamAssignment).where(TeamAssignment.id == assignment_id))
        ).scalar_one_or_none()
        assert remaining is None  # hard-deleted

        fresh = (
            await vs.execute(select(VolunteerCall).where(VolunteerCall.id == call_id))
        ).scalar_one()
        assert fresh.assignments_changed_at is not None
        assert vol_id not in fresh.last_sent_roster[task_id]["assigned"]

    # Lead + admin notified with the message; volunteer got a brief ack.
    assert "lead@example.com" in rec.recipients
    assert "admin@example.com" in rec.recipients
    lead_body = rec.to("lead@example.com")[0][2]
    assert "Sorry Lee, cannot make it that day." in lead_body
    assert "Vic Volunteer" in lead_body
    vol_msgs = rec.to("vol@example.com")
    assert vol_msgs and "Assignment update" in vol_msgs[0][1]


@pytest.mark.asyncio
async def test_cannot_decline_someone_elses_assignment(engine, db: AsyncSession) -> None:
    """A volunteer must not be able to decline another person's assignment by
    guessing its id. Catches a missing server-side ownership check."""
    s = await _seed(db)
    try:
        async with _client(engine, s["other"].id) as client:
            resp = await client.post(
                f"/api/volunteering/my-assignments/{s['vol_assignment'].id}/decline",
                json={},
            )
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cannot_decline_on_archived_call(engine, db: AsyncSession) -> None:
    """Once a call is archived, declines are rejected. Catches a missing
    status gate."""
    s = await _seed(db, status=CallStatus.ARCHIVED)
    try:
        async with _client(engine, s["vol"].id) as client:
            resp = await client.post(
                f"/api/volunteering/my-assignments/{s['vol_assignment'].id}/decline",
                json={},
            )
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_my_assignments_includes_task_id_and_team_lead_name(
    engine, db: AsyncSession
) -> None:
    """The volunteer view needs the task id (to match calendar conflicts) and
    the team lead's name (to prefill the decline message). Catches dropping
    either field from the response."""
    s = await _seed(db)
    try:
        async with _client(engine, s["vol"].id) as client:
            resp = await client.get("/api/volunteering/my-assignments")
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    rows = {r["assignment_id"]: r for r in resp.json()}
    mine = rows[s["vol_assignment"].id]
    assert mine["task_id"] == s["task"].id
    assert mine["team_lead_name"] == "Lee Lead"
