"""Tests for the cross-call fairness signals on /assignment-overview.

Bugs each test catches:

- test_last_assignment_date_uses_max_task_date: regression where
  last_assignment_date is computed from the current call only, instead of
  picking the most recent Task.date across every TeamAssignment for the
  person. A volunteer assigned in last week's call would report None.
- test_trailing_3mo_excludes_older_assignments: regression where the
  trailing window includes assignments older than 90 days, so the count
  drifts upward over time and the 😴-detection percentile becomes useless.
- test_volunteers_sorted_by_first_name: regression where the response
  preserves insertion order or sorts by last_name, contradicting the
  product decision that admins know volunteers by first name.
- test_first_name_and_last_name_fields_populated: ensures the response
  carries split name fields the frontend needs for first-name sort + the
  display "First L." format in the spreadsheet view.
"""

import datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from volunteer_call_api.database import get_db
from volunteer_call_api.dependencies import get_current_user
from volunteer_call_api.main import app
from volunteer_call_api.models import Base, Person, PersonRole
from volunteer_call_api.models.person import Program, RoleType, VolunteerProgram
from volunteer_call_api.models.team_assignment import AssignmentRole, TeamAssignment
from volunteer_call_api.models.volunteer_availability import VolunteerAvailability
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
        return Person(first_name="Admin", last_name="Tester", active=True)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _stub_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _seed_volunteer(
    db: AsyncSession,
    first_name: str,
    last_name: str,
    email: str,
) -> Person:
    person = Person(first_name=first_name, last_name=last_name, email=email, active=True)
    db.add(person)
    await db.flush()
    db.add(PersonRole(person_id=person.id, role=RoleType.VOLUNTEER))
    db.add(VolunteerProgram(person_id=person.id, program=Program.RTX))
    await db.commit()
    return person


async def _seed_call_with_task(
    db: AsyncSession,
    title: str,
    task_date: datetime.date,
) -> tuple[VolunteerCall, Task]:
    call = VolunteerCall(title=title, program=Program.RTX, status=CallStatus.WAITING)
    db.add(call)
    await db.flush()
    task = Task(
        volunteer_call_id=call.id,
        short_description=f"{title} task",
        date=task_date,
        volunteers_needed=2,
    )
    db.add(task)
    await db.commit()
    return call, task


async def _seed_availability(
    db: AsyncSession, person: Person, call: VolunteerCall, task: Task
) -> None:
    db.add(
        VolunteerAvailability(
            volunteer_call_id=call.id,
            person_id=person.id,
            task_id=task.id,
            available=True,
            max_tasks_per_week=2,
        )
    )
    await db.commit()


async def _assign(db: AsyncSession, person: Person, task: Task) -> None:
    db.add(
        TeamAssignment(
            task_id=task.id,
            person_id=person.id,
            role=AssignmentRole.VOLUNTEER,
        )
    )
    await db.commit()


@pytest.mark.asyncio
async def test_last_assignment_date_uses_max_task_date(
    db: AsyncSession, client: AsyncClient
) -> None:
    # Vick was assigned to a task 30 days ago and another 5 days ago. Last
    # date should be 5 days ago — the max, not the most recently *created*.
    vick = await _seed_volunteer(db, "Vick", "Fisher", "vick@example.com")
    old_call, old_task = await _seed_call_with_task(
        db, "Old call", TODAY - datetime.timedelta(days=30)
    )
    await _assign(db, vick, old_task)
    recent_call, recent_task = await _seed_call_with_task(
        db, "Recent call", TODAY - datetime.timedelta(days=5)
    )
    await _assign(db, vick, recent_task)
    # Current call (no assignments yet — Vick is responding):
    current_call, current_task = await _seed_call_with_task(
        db, "Current call", TODAY + datetime.timedelta(days=2)
    )
    await _seed_availability(db, vick, current_call, current_task)

    resp = await client.get(f"/api/volunteer-calls/{current_call.id}/assignment-overview")
    assert resp.status_code == 200
    vols = resp.json()["volunteers"]
    assert len(vols) == 1
    assert vols[0]["last_assignment_date"] == (TODAY - datetime.timedelta(days=5)).isoformat()


@pytest.mark.asyncio
async def test_trailing_3mo_excludes_older_assignments(
    db: AsyncSession, client: AsyncClient
) -> None:
    # 4 assignments: 200 days, 100 days, 30 days, 5 days ago. The 90-day
    # window catches only the last two.
    bryan = await _seed_volunteer(db, "Bryan", "Cobb", "bryan@example.com")
    for days in (200, 100, 30, 5):
        _, task = await _seed_call_with_task(
            db, f"Call {days}d ago", TODAY - datetime.timedelta(days=days)
        )
        await _assign(db, bryan, task)
    current_call, current_task = await _seed_call_with_task(
        db, "Current", TODAY + datetime.timedelta(days=1)
    )
    await _seed_availability(db, bryan, current_call, current_task)

    resp = await client.get(f"/api/volunteer-calls/{current_call.id}/assignment-overview")
    assert resp.status_code == 200
    vols = resp.json()["volunteers"]
    assert vols[0]["assignments_trailing_3mo"] == 2


@pytest.mark.asyncio
async def test_volunteers_sorted_by_first_name(db: AsyncSession, client: AsyncClient) -> None:
    # Seed in non-alphabetical order; expect first-name alphabetical out.
    zara = await _seed_volunteer(db, "Zara", "Adams", "z@example.com")
    alex = await _seed_volunteer(db, "alex", "Zimmerman", "a@example.com")  # lowercase
    marg = await _seed_volunteer(db, "Margaret", "Brown", "m@example.com")
    current_call, current_task = await _seed_call_with_task(
        db, "Current", TODAY + datetime.timedelta(days=1)
    )
    for v in (zara, alex, marg):
        await _seed_availability(db, v, current_call, current_task)

    resp = await client.get(f"/api/volunteer-calls/{current_call.id}/assignment-overview")
    first_names = [v["first_name"] for v in resp.json()["volunteers"]]
    # Case-insensitive: "alex" sorts before "Margaret" before "Zara".
    assert first_names == ["alex", "Margaret", "Zara"]


@pytest.mark.asyncio
async def test_first_name_and_last_name_fields_populated(
    db: AsyncSession, client: AsyncClient
) -> None:
    don = await _seed_volunteer(db, "Don", "Ryan", "don@example.com")
    call, task = await _seed_call_with_task(db, "Cur", TODAY + datetime.timedelta(days=3))
    await _seed_availability(db, don, call, task)
    # Pre-assign Don so we exercise the TaskAssignment + AvailableVolunteer
    # serializers both.
    await _assign(db, don, task)
    other = await _seed_volunteer(db, "Bert", "Lee", "bert@example.com")
    await _seed_availability(db, other, call, task)

    resp = await client.get(f"/api/volunteer-calls/{call.id}/assignment-overview")
    body = resp.json()
    # Assigned row
    a = body["tasks"][0]["assignments"][0]
    assert a["first_name"] == "Don"
    assert a["last_name"] == "Ryan"
    # Available row
    av = body["tasks"][0]["available_volunteers"][0]
    assert av["first_name"] == "Bert"
    assert av["last_name"] == "Lee"


@pytest.mark.asyncio
async def test_volunteer_with_no_history_has_null_last_date(
    db: AsyncSession, client: AsyncClient
) -> None:
    # Brand-new volunteer never assigned anywhere — last_assignment_date
    # must be None, not silently 0/today. Catches a coalesce-to-now bug.
    newbie = await _seed_volunteer(db, "Newbie", "First", "n@example.com")
    call, task = await _seed_call_with_task(db, "Cur", TODAY + datetime.timedelta(days=2))
    await _seed_availability(db, newbie, call, task)

    resp = await client.get(f"/api/volunteer-calls/{call.id}/assignment-overview")
    vols = resp.json()["volunteers"]
    assert vols[0]["last_assignment_date"] is None
    assert vols[0]["assignments_trailing_3mo"] == 0
