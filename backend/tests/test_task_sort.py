"""Bug each test catches:

- test_tasks_sorted_by_date_in_call_response: regression where a task
  added later but scheduled earlier shows up below an earlier-added but
  later-scheduled task. The call detail view, email, and assign view all
  rely on chronological order, so getting this wrong silently breaks
  every downstream consumer.
- test_undated_tasks_sink_to_bottom: regression where NULL date sorts as
  the smallest value (Python default), pushing undated tasks to the top.
  Admins expect dated tasks first, undated last.
- test_first_name_sort_in_people_endpoint: regression where the /people
  list orders by last_name first, contradicting the product decision to
  sort by first name across the app.
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
from volunteer_call_api.models.person import Program, RoleType
from volunteer_call_api.models.volunteer_call import CallStatus, Task, VolunteerCall


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


@pytest.mark.asyncio
async def test_tasks_sorted_by_date_in_call_response(
    db: AsyncSession, client: AsyncClient
) -> None:
    call = VolunteerCall(title="Spring", program=Program.RTX, status=CallStatus.OPEN)
    db.add(call)
    await db.flush()
    # Insert in reverse-chronological order; expect chronological out.
    db.add(Task(volunteer_call_id=call.id, short_description="Third", date=datetime.date(2025, 12, 12)))
    db.add(Task(volunteer_call_id=call.id, short_description="First", date=datetime.date(2025, 11, 1)))
    db.add(Task(volunteer_call_id=call.id, short_description="Second", date=datetime.date(2025, 11, 15)))
    await db.commit()

    resp = await client.get(f"/api/volunteer-calls/{call.id}")
    assert resp.status_code == 200
    descriptions = [t["short_description"] for t in resp.json()["tasks"]]
    assert descriptions == ["First", "Second", "Third"]


@pytest.mark.asyncio
async def test_undated_tasks_sink_to_bottom(
    db: AsyncSession, client: AsyncClient
) -> None:
    call = VolunteerCall(title="Mixed", program=Program.RTX, status=CallStatus.OPEN)
    db.add(call)
    await db.flush()
    db.add(Task(volunteer_call_id=call.id, short_description="No date", date=None))
    db.add(Task(volunteer_call_id=call.id, short_description="Dec", date=datetime.date(2025, 12, 1)))
    db.add(Task(volunteer_call_id=call.id, short_description="Nov", date=datetime.date(2025, 11, 1)))
    await db.commit()

    resp = await client.get(f"/api/volunteer-calls/{call.id}")
    assert resp.status_code == 200
    descriptions = [t["short_description"] for t in resp.json()["tasks"]]
    assert descriptions == ["Nov", "Dec", "No date"]


@pytest.mark.asyncio
async def test_first_name_sort_in_people_endpoint(
    db: AsyncSession, client: AsyncClient
) -> None:
    # Three volunteers with deliberately misleading last-name order:
    # last-name sort would give Aronson, Davies, Williams; first-name
    # sort gives Bryan, Vick, Zara — distinct enough to detect the bug.
    for first, last in (("Vick", "Aronson"), ("Zara", "Davies"), ("Bryan", "Williams")):
        person = Person(first_name=first, last_name=last, email=f"{first}@example.com", active=True)
        db.add(person)
        await db.flush()
        db.add(PersonRole(person_id=person.id, role=RoleType.VOLUNTEER))
    await db.commit()

    resp = await client.get("/api/people")
    assert resp.status_code == 200
    first_names = [p["first_name"] for p in resp.json()]
    assert first_names == ["Bryan", "Vick", "Zara"]
