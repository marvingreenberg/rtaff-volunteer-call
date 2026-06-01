"""Behavior tests for change-aware assignment notifications.

These exercise `generate_call_notifications` end-to-end against an in-memory
DB, capturing who gets emailed and what their email says. The grouping logic
(per-person, not per-task) and the email content (team roster + "(Updated)"
markers, brief removal ack, lead "(added)"/"(removed)" markers) are the
behaviors under test.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

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


@dataclass
class Sent:
    email: str
    subject: str
    full_body: str


class Recorder:
    """Stand-in for deliver_notification that records what would be sent."""

    def __init__(self) -> None:
        self.sent: list[Sent] = []

    def __call__(self, *, person, subject, full_body, summary_body, **kwargs) -> bool:
        self.sent.append(Sent(email=person.email or "", subject=subject, full_body=full_body))
        return True

    def to(self, email: str) -> list[Sent]:
        return [s for s in self.sent if s.email == email]

    @property
    def recipients(self) -> set[str]:
        return {s.email for s in self.sent}


async def _person(db: AsyncSession, first: str, email: str) -> Person:
    p = Person(first_name=first, last_name="X", email=email)
    db.add(p)
    await db.flush()
    return p


async def _call_with_task(db: AsyncSession, *, with_lead: Person | None = None) -> tuple[str, Task]:
    call = VolunteerCall(title="June Repair", program=Program.RTX, status=CallStatus.ASSIGNED)
    db.add(call)
    await db.flush()
    task = Task(
        volunteer_call_id=call.id,
        short_description="Replace ceiling fan",
        date=JOB_DATE,
        time_start=datetime.time(9, 0),
        address="500 Oak Ave",
        city="Arlington",
        volunteers_needed=4,
        team_lead_id=with_lead.id if with_lead else None,
    )
    db.add(task)
    await db.flush()
    return call.id, task


async def _assign(db: AsyncSession, task: Task, person: Person) -> TeamAssignment:
    a = TeamAssignment(task_id=task.id, person_id=person.id, role=AssignmentRole.VOLUNTEER)
    db.add(a)
    await db.flush()
    return a


async def _send(engine, call_id: str) -> Recorder:
    """Run a notification pass in its own session (like a real request) with
    deliver_notification captured, committing so last_sent_roster persists for
    the next pass. A fresh session avoids reusing stale relationship
    collections from the seeding session."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    rec = Recorder()
    async with factory() as session:
        with patch.object(notifications, "deliver_notification", rec):
            await notifications.generate_call_notifications(call_id, session)
        await session.commit()
    return rec


@pytest.mark.asyncio
async def test_first_send_emails_all_assignees_with_team_roster_and_no_markers(
    engine, db: AsyncSession
) -> None:
    """First send goes to everyone, each email lists the whole team, and there
    are no '(Updated)' markers because nothing has changed yet. Catches a
    regression that suppresses first-send emails or shows spurious markers."""
    alice = await _person(db, "Alice", "alice@example.com")
    bob = await _person(db, "Bob", "bob@example.com")
    call_id, task = await _call_with_task(db)
    await _assign(db, task, alice)
    await _assign(db, task, bob)
    await db.commit()

    rec = await _send(engine, call_id)

    assert rec.recipients == {"alice@example.com", "bob@example.com"}
    assert "Bob" in rec.to("alice@example.com")[0].full_body  # roster lists teammate
    assert "Alice" in rec.to("bob@example.com")[0].full_body
    assert "(Updated)" not in rec.to("alice@example.com")[0].full_body


@pytest.mark.asyncio
async def test_adding_a_volunteer_emails_all_assignees_with_updated_team(
    engine, db: AsyncSession
) -> None:
    """Adding one volunteer must email *everyone* on the task (their team list
    changed), each email shows the new member, and the Team section is marked
    '(Updated)'. Catches the old per-task bug where unchanged teammates either
    got nothing or got a meaningless 'may be unchanged' email."""
    alice = await _person(db, "Alice", "alice@example.com")
    bob = await _person(db, "Bob", "bob@example.com")
    carol = await _person(db, "Carol", "carol@example.com")
    call_id, task = await _call_with_task(db)
    await _assign(db, task, alice)
    await _assign(db, task, bob)
    await db.commit()
    await _send(engine, call_id)  # first send establishes the baseline

    await _assign(db, task, carol)
    await db.commit()
    rec = await _send(engine, call_id)

    assert rec.recipients == {"alice@example.com", "bob@example.com", "carol@example.com"}
    # Every recipient (including the unchanged Alice/Bob) sees the new member.
    for email in rec.recipients:
        assert "Carol" in rec.to(email)[0].full_body
    assert "(Updated)" in rec.to("alice@example.com")[0].full_body


@pytest.mark.asyncio
async def test_removal_only_emails_only_the_removed_volunteer(engine, db: AsyncSession) -> None:
    """When the only change is a removal, the remaining teammates get nothing —
    only the removed volunteer gets a brief acknowledgement (city + date, no
    street address). Catches over-notifying teammates on a drop and leaking
    project details into the brief ack."""
    alice = await _person(db, "Alice", "alice@example.com")
    bob = await _person(db, "Bob", "bob@example.com")
    carol = await _person(db, "Carol", "carol@example.com")
    call_id, task = await _call_with_task(db)
    a_alice = await _assign(db, task, alice)  # noqa: F841
    await _assign(db, task, bob)
    carol_assignment = await _assign(db, task, carol)
    await db.commit()
    await _send(engine, call_id)

    await db.delete(carol_assignment)
    await db.commit()
    rec = await _send(engine, call_id)

    assert rec.recipients == {"carol@example.com"}
    body = rec.to("carol@example.com")[0].full_body
    assert "Arlington" in body  # city is in the brief ack
    assert "500 Oak Ave" not in body  # but not the street address


@pytest.mark.asyncio
async def test_time_change_emails_all_assignees_with_time_marked_updated(
    engine, db: AsyncSession
) -> None:
    """A schedule edit reaches every assignee with the time section flagged
    '(Updated)'. Catches a missing per-field detail diff."""
    alice = await _person(db, "Alice", "alice@example.com")
    bob = await _person(db, "Bob", "bob@example.com")
    call_id, task = await _call_with_task(db)
    await _assign(db, task, alice)
    await _assign(db, task, bob)
    await db.commit()
    await _send(engine, call_id)

    task.time_start = datetime.time(11, 0)
    await db.commit()
    rec = await _send(engine, call_id)

    assert rec.recipients == {"alice@example.com", "bob@example.com"}
    assert "(Updated)" in rec.to("alice@example.com")[0].full_body


@pytest.mark.asyncio
async def test_lead_roster_marks_added_and_removed_for_staff_edits(
    engine, db: AsyncSession
) -> None:
    """The team lead's roster email flags who joined and who left since the
    last send. Catches the lead being unable to see roster churn."""
    lead = await _person(db, "Lead", "lead@example.com")
    alice = await _person(db, "Alice", "alice@example.com")
    bob = await _person(db, "Bob", "bob@example.com")
    carol = await _person(db, "Carol", "carol@example.com")
    call_id, task = await _call_with_task(db, with_lead=lead)
    await _assign(db, task, alice)
    bob_assignment = await _assign(db, task, bob)
    await db.commit()
    await _send(engine, call_id)

    await db.delete(bob_assignment)
    await _assign(db, task, carol)
    await db.commit()
    rec = await _send(engine, call_id)

    lead_body = rec.to("lead@example.com")[0].full_body
    assert "(added)" in lead_body
    assert "(removed)" in lead_body
    assert "Carol" in lead_body
    assert "Bob" in lead_body


@pytest.mark.asyncio
async def test_notify_decline_emails_lead_admin_and_volunteer(engine, db: AsyncSession) -> None:
    """A decline notifies the team lead and the call admin (distinct people)
    and sends the declining volunteer a brief ack — three recipients. Catches a
    notify path that forgets the admin or the volunteer ack."""
    admin = await _person(db, "Ada", "admin@example.com")
    lead = await _person(db, "Lee", "lead@example.com")
    vol = await _person(db, "Vic", "vol@example.com")
    call = VolunteerCall(
        title="June", program=Program.RTX, status=CallStatus.ASSIGNED, created_by_id=admin.id
    )
    db.add(call)
    await db.flush()
    task = Task(
        volunteer_call_id=call.id,
        short_description="Fix steps",
        date=JOB_DATE,
        city="Arlington",
        team_lead_id=lead.id,
    )
    db.add(task)
    await db.flush()
    await db.commit()

    rec = Recorder()
    with patch.object(notifications, "deliver_notification", rec):
        await notifications.notify_decline(call.id, task.id, vol.id, "Cannot make it", db)

    assert rec.recipients == {"admin@example.com", "lead@example.com", "vol@example.com"}


@pytest.mark.asyncio
async def test_notify_decline_dedupes_when_admin_is_the_team_lead(engine, db: AsyncSession) -> None:
    """When the call admin is also the task's team lead, they get exactly one
    roster email — not two. Catches a missing dedupe that would double-email."""
    admin_lead = await _person(db, "Sam", "samlead@example.com")
    vol = await _person(db, "Vic", "vol@example.com")
    call = VolunteerCall(
        title="June",
        program=Program.RTX,
        status=CallStatus.ASSIGNED,
        created_by_id=admin_lead.id,
    )
    db.add(call)
    await db.flush()
    task = Task(
        volunteer_call_id=call.id,
        short_description="Fix steps",
        date=JOB_DATE,
        city="Arlington",
        team_lead_id=admin_lead.id,
    )
    db.add(task)
    await db.flush()
    await db.commit()

    rec = Recorder()
    with patch.object(notifications, "deliver_notification", rec):
        await notifications.notify_decline(call.id, task.id, vol.id, None, db)

    assert len(rec.to("samlead@example.com")) == 1
    assert rec.recipients == {"samlead@example.com", "vol@example.com"}
