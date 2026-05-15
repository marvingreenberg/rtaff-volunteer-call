"""Tests for /volunteer-calls/{id}/auto-assign-team-leads.

Bugs each test catches:

- test_only_fills_unstaffed_tasks: regression where the auto-pick
  overwrites an already-assigned team lead. Admins lose intentional picks.
- test_picks_program_matched_leads: regression where the heuristic
  considers any team-leader, including ones outside the call's program.
- test_spreads_across_leads_within_a_call: regression where the same
  least-recently-assigned lead gets picked for every task in the call,
  producing one overworked lead and an entire pool of fresh ones.
- test_avoids_same_date_double_booking_within_call: regression where two
  same-date tasks both get the same lead, putting them on overlapping
  schedules in one click.
- test_returns_zero_when_no_eligible_leads: regression where the endpoint
  crashes or silently picks a non-team-leader because the leads list is
  empty for the call's program.
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
        return Person(first_name="Admin", last_name="T", active=True)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _stub_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _seed_lead(
    db: AsyncSession,
    first: str,
    *,
    program: Program = Program.RTX,
) -> Person:
    p = Person(first_name=first, last_name="Leader", email=f"{first}@example.com", active=True)
    db.add(p)
    await db.flush()
    db.add(PersonRole(person_id=p.id, role=RoleType.TEAM_LEADER))
    db.add(VolunteerProgram(person_id=p.id, program=program))
    await db.commit()
    return p


async def _seed_call(
    db: AsyncSession,
    title: str,
    *,
    program: Program = Program.RTX,
) -> VolunteerCall:
    call = VolunteerCall(title=title, program=program, status=CallStatus.WAITING)
    db.add(call)
    await db.commit()
    return call


async def _add_task(
    db: AsyncSession,
    call: VolunteerCall,
    date: datetime.date | None,
    *,
    team_lead_id: str | None = None,
) -> Task:
    task = Task(
        volunteer_call_id=call.id,
        short_description=f"Task @ {date}",
        date=date,
        volunteers_needed=2,
        team_lead_id=team_lead_id,
    )
    db.add(task)
    await db.commit()
    return task


@pytest.mark.asyncio
async def test_only_fills_unstaffed_tasks(db: AsyncSession, client: AsyncClient) -> None:
    pre_lead = await _seed_lead(db, "Pre")
    fresh_lead = await _seed_lead(db, "Fresh")
    call = await _seed_call(db, "Cur")
    pre_task = await _add_task(
        db, call, TODAY + datetime.timedelta(days=2), team_lead_id=pre_lead.id
    )
    empty_task = await _add_task(db, call, TODAY + datetime.timedelta(days=3))

    resp = await client.post(f"/api/volunteer-calls/{call.id}/auto-assign-team-leads")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tasks_updated"] == 1

    await db.refresh(pre_task)
    await db.refresh(empty_task)
    # Pre-assigned task: leader unchanged.
    assert pre_task.team_lead_id == pre_lead.id
    # Empty task: now has a lead.
    assert empty_task.team_lead_id == fresh_lead.id


@pytest.mark.asyncio
async def test_picks_program_matched_leads(db: AsyncSession, client: AsyncClient) -> None:
    # Out-of-program lead must NOT be picked — even if they're the only
    # team leader in the system.
    await _seed_lead(db, "Acr", program=Program.ACR)
    rtx_lead = await _seed_lead(db, "Rtx", program=Program.RTX)
    call = await _seed_call(db, "Rtx call", program=Program.RTX)
    task = await _add_task(db, call, TODAY + datetime.timedelta(days=2))

    resp = await client.post(f"/api/volunteer-calls/{call.id}/auto-assign-team-leads")
    assert resp.status_code == 200
    await db.refresh(task)
    assert task.team_lead_id == rtx_lead.id


@pytest.mark.asyncio
async def test_spreads_across_leads_within_a_call(db: AsyncSession, client: AsyncClient) -> None:
    # Three leads, three tasks on different dates, no prior history.
    # Heuristic should not pick the same lead three times.
    leads = [await _seed_lead(db, name) for name in ("Adam", "Bea", "Cara")]
    call = await _seed_call(db, "Cur")
    tasks = [await _add_task(db, call, TODAY + datetime.timedelta(days=d)) for d in (2, 3, 4)]
    resp = await client.post(f"/api/volunteer-calls/{call.id}/auto-assign-team-leads")
    assert resp.status_code == 200
    picked = set()
    for t in tasks:
        await db.refresh(t)
        picked.add(t.team_lead_id)
    assert len(picked) == 3, f"each task should pick a distinct lead, got {picked}"
    assert picked == {l.id for l in leads}


@pytest.mark.asyncio
async def test_avoids_same_date_double_booking_within_call(
    db: AsyncSession, client: AsyncClient
) -> None:
    # Two tasks on the SAME date, two leads — each task must get a different lead.
    leads = [await _seed_lead(db, name) for name in ("Adam", "Bea")]
    call = await _seed_call(db, "Cur")
    same_date = TODAY + datetime.timedelta(days=5)
    t1 = await _add_task(db, call, same_date)
    t2 = await _add_task(db, call, same_date)
    resp = await client.post(f"/api/volunteer-calls/{call.id}/auto-assign-team-leads")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tasks_updated"] == 2
    await db.refresh(t1)
    await db.refresh(t2)
    assert t1.team_lead_id != t2.team_lead_id
    assert {t1.team_lead_id, t2.team_lead_id} == {l.id for l in leads}


@pytest.mark.asyncio
async def test_skips_when_no_more_leads_available_same_date(
    db: AsyncSession, client: AsyncClient
) -> None:
    # One lead, two same-date tasks: lead can only take one. Second task
    # is left unstaffed and counted in `tasks_skipped` — better than
    # silently double-booking the only lead onto two same-day projects.
    lead = await _seed_lead(db, "OnlyOne")
    call = await _seed_call(db, "Cur")
    same_date = TODAY + datetime.timedelta(days=5)
    t1 = await _add_task(db, call, same_date)
    t2 = await _add_task(db, call, same_date)
    resp = await client.post(f"/api/volunteer-calls/{call.id}/auto-assign-team-leads")
    body = resp.json()
    assert body["tasks_updated"] == 1
    assert body["tasks_skipped"] == 1
    await db.refresh(t1)
    await db.refresh(t2)
    leads_set = {t1.team_lead_id, t2.team_lead_id}
    assert lead.id in leads_set
    assert None in leads_set


@pytest.mark.asyncio
async def test_returns_zero_when_no_eligible_leads(db: AsyncSession, client: AsyncClient) -> None:
    call = await _seed_call(db, "Cur")
    await _add_task(db, call, TODAY + datetime.timedelta(days=2))
    resp = await client.post(f"/api/volunteer-calls/{call.id}/auto-assign-team-leads")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tasks_updated"] == 0
    assert body["tasks_skipped"] == 1


@pytest.mark.asyncio
async def test_prefers_least_recently_assigned_lead(db: AsyncSession, client: AsyncClient) -> None:
    # Two leads. Recent has a recent assignment, Idle has none. Single
    # empty task should pick Idle, not Recent.
    recent = await _seed_lead(db, "Recent")
    idle = await _seed_lead(db, "Idle")
    # Give Recent a historical assignment.
    other_call = await _seed_call(db, "Old call")
    other_task = await _add_task(db, other_call, TODAY - datetime.timedelta(days=5))
    db.add(
        TeamAssignment(task_id=other_task.id, person_id=recent.id, role=AssignmentRole.TEAM_LEADER)
    )
    await db.commit()

    call = await _seed_call(db, "Cur")
    task = await _add_task(db, call, TODAY + datetime.timedelta(days=2))
    resp = await client.post(f"/api/volunteer-calls/{call.id}/auto-assign-team-leads")
    assert resp.status_code == 200
    await db.refresh(task)
    assert task.team_lead_id == idle.id
