"""Bug each test catches:

- test_update_task_with_assignment_returns_200: regression where
  routes/volunteer_calls.py::update_task re-fetched the task with
  ``selectinload(Task.assignments)`` but did not chain into
  ``TeamAssignment.person``. The subsequent ``task_response(task)`` call
  iterates ``task.assignments`` and reads ``a.person`` — without the
  eager load that triggers a lazy-load outside the async greenlet, which
  raises ``sqlalchemy.exc.MissingGreenlet`` and returns 500. The bug
  only surfaces when the task has at least one assignment, which is
  exactly the common case after the admin has staffed a task.
- test_create_task_response_carries_assignees: same eager-load shape on
  the POST path. Less visible than the PUT path because freshly-created
  tasks have no assignments, but the moment an assignment exists and
  the admin re-saves, the PUT path is on the hook. Pinning both
  endpoints keeps them from drifting independently.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from volunteer_call_api.database import get_db
from volunteer_call_api.dependencies import get_current_user
from volunteer_call_api.main import app
from volunteer_call_api.models import Base, Person, PersonRole
from volunteer_call_api.models.person import Program, RoleType
from volunteer_call_api.models.team_assignment import AssignmentRole, TeamAssignment
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
async def test_update_task_with_assignment_returns_200(
    db: AsyncSession, client: AsyncClient
) -> None:
    call = VolunteerCall(title="Spring", program=Program.RTX, status=CallStatus.OPEN)
    db.add(call)
    await db.flush()

    task = Task(
        volunteer_call_id=call.id,
        short_description="Original description",
        volunteers_needed=2,
    )
    db.add(task)
    await db.flush()

    volunteer = Person(first_name="Lee", last_name="Rubis", email="lee@example.com", active=True)
    db.add(volunteer)
    await db.flush()
    db.add(PersonRole(person_id=volunteer.id, role=RoleType.VOLUNTEER))
    db.add(TeamAssignment(task_id=task.id, person_id=volunteer.id, role=AssignmentRole.VOLUNTEER))
    await db.commit()

    resp = await client.put(
        f"/api/volunteer-calls/{call.id}/tasks/{task.id}",
        json={"short_description": "Updated description"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["short_description"] == "Updated description"
    assert body["assigned_count"] == 1
    assert len(body["assignees"]) == 1
    assignee = body["assignees"][0]
    assert assignee["first_name"] == "Lee"
    assert assignee["last_name"] == "Rubis"
    assert assignee["initials"] == "LR"


@pytest.mark.asyncio
async def test_create_task_response_carries_assignees(
    db: AsyncSession, client: AsyncClient
) -> None:
    # Mirror coverage on the POST path. A fresh task has no assignments yet,
    # so the body should reflect that without triggering a lazy load.
    call = VolunteerCall(title="Autumn", program=Program.RTX, status=CallStatus.OPEN)
    db.add(call)
    await db.commit()

    resp = await client.post(
        f"/api/volunteer-calls/{call.id}/tasks",
        json={"short_description": "Brand new", "volunteers_needed": 3},
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["short_description"] == "Brand new"
    assert body["assigned_count"] == 0
    assert body["assignees"] == []
