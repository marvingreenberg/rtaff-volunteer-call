"""Tests for GET /api/people pagination + filter-aware total.

Bugs each test catches:

- ``test_total_is_filter_count_not_page_size``: regression where
  ``total`` collapses to ``len(items)`` or to ``count``, hiding the
  real "N of TOTAL" from the admin. This is the exact bug the People
  page surfaced when 57 volunteers in the DB showed up as "21
  volunteers" in the header.
- ``test_pagination_independent_of_total``: regression where the
  count query inherits the LIMIT/OFFSET from the items query, so
  ``total`` shrinks as you page.
- ``test_role_filter_total_matches_count_distinct``: regression
  where joining ``Person.roles`` multiplies the count for people
  with multiple roles (e.g. the team-leads who also have a
  ``volunteer`` PersonRole).
- ``test_count_param_caps_at_max``: regression where MAX_PEOPLE_PAGE_SIZE
  is dropped and a misbehaving client can ask for the whole table.
- ``test_start_beyond_total_returns_empty_items_real_total``:
  regression where querying past the end either 500s or returns
  ``total=0``; the correct shape is empty items + the real total.
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
from volunteer_call_api.models.person import RoleType


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


async def _seed_volunteers(db: AsyncSession, n: int) -> None:
    """Create n people, all with a VOLUNTEER PersonRole. Names sorted by
    first-name match the API's order_by so test assertions are stable."""
    for i in range(n):
        # Two-letter first names so sort order is deterministic across
        # double-digit i (A1, A2, ... A9, B0, ...).
        first = f"V{i:03d}"
        p = Person(first_name=first, last_name="Test", active=True)
        db.add(p)
        await db.flush()
        db.add(PersonRole(person_id=p.id, role=RoleType.VOLUNTEER))
    await db.commit()


@pytest.mark.asyncio
async def test_total_is_filter_count_not_page_size(client: AsyncClient, db: AsyncSession) -> None:
    await _seed_volunteers(db, 30)
    resp = await client.get("/api/people?count=10")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 30
    assert len(body["items"]) == 10
    assert body["start"] == 0
    assert body["count"] == 10


@pytest.mark.asyncio
async def test_pagination_independent_of_total(client: AsyncClient, db: AsyncSession) -> None:
    await _seed_volunteers(db, 30)
    page1 = await client.get("/api/people?start=0&count=10")
    page2 = await client.get("/api/people?start=10&count=10")
    page3 = await client.get("/api/people?start=20&count=10")
    # Total stays constant; items differ.
    assert page1.json()["total"] == 30
    assert page2.json()["total"] == 30
    assert page3.json()["total"] == 30
    ids1 = {p["id"] for p in page1.json()["items"]}
    ids2 = {p["id"] for p in page2.json()["items"]}
    ids3 = {p["id"] for p in page3.json()["items"]}
    assert ids1.isdisjoint(ids2)
    assert ids2.isdisjoint(ids3)
    assert len(ids1 | ids2 | ids3) == 30


@pytest.mark.asyncio
async def test_role_filter_total_matches_count_distinct(
    client: AsyncClient, db: AsyncSession
) -> None:
    """A person with multiple PersonRole rows (e.g. team-leads who also
    have volunteer) must count as 1 under a role filter, not N."""
    # 5 volunteer-only + 3 team-leads with BOTH volunteer + team_leader.
    for i in range(5):
        p = Person(first_name=f"Vol{i}", last_name="X", active=True)
        db.add(p)
        await db.flush()
        db.add(PersonRole(person_id=p.id, role=RoleType.VOLUNTEER))
    for i in range(3):
        p = Person(first_name=f"Lead{i}", last_name="X", active=True)
        db.add(p)
        await db.flush()
        db.add(PersonRole(person_id=p.id, role=RoleType.TEAM_LEADER))
        db.add(PersonRole(person_id=p.id, role=RoleType.VOLUNTEER))
    await db.commit()

    resp = await client.get("/api/people?role=volunteer&count=50")
    assert resp.status_code == 200
    body = resp.json()
    # 5 volunteer-only + 3 dual-role = 8 distinct volunteers.
    assert body["total"] == 8
    assert len(body["items"]) == 8


@pytest.mark.asyncio
async def test_count_param_caps_at_max(client: AsyncClient, db: AsyncSession) -> None:
    await _seed_volunteers(db, 5)
    resp = await client.get("/api/people?count=10000")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_start_beyond_total_returns_empty_items_real_total(
    client: AsyncClient, db: AsyncSession
) -> None:
    await _seed_volunteers(db, 5)
    resp = await client.get("/api/people?start=100&count=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 5
