"""Tests for email-alias login.

Bugs each test catches:

- test_login_by_alias_finds_person: regression where the /login route
  only matches Person.email and never consults person_login_aliases —
  a user with a valid alias would get 404.
- test_login_by_alias_sends_link_to_typed_address: regression where
  the magic-link email is sent to person.email (the notification
  inbox) instead of the address the user typed, defeating the purpose
  of aliasing.
- test_primary_login_is_case_insensitive: regression where users with
  mixed-case stored primary emails can't log in if they don't type
  the exact original casing.
- test_alias_email_globally_unique: regression where two rows in
  person_login_aliases share the same email, making login ambiguous.
- test_unknown_email_still_rejected: ensures the new fallback lookup
  doesn't accidentally treat unknown emails as valid.
"""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from volunteer_call_api.database import get_db
from volunteer_call_api.main import app
from volunteer_call_api.models import Base, Person, PersonLoginAlias
from volunteer_call_api.services.login_throttle import login_throttle


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

    app.dependency_overrides[get_db] = override_get_db
    login_throttle._reset()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    login_throttle._reset()


async def _seed_person_with_alias(db: AsyncSession, primary: str, alias: str) -> Person:
    person = Person(first_name="Ada", last_name="Lovelace", email=primary, active=True)
    db.add(person)
    await db.flush()
    db.add(PersonLoginAlias(person_id=person.id, email=alias))
    await db.commit()
    return person


@pytest.mark.asyncio
async def test_login_by_alias_finds_person(client: AsyncClient, db: AsyncSession) -> None:
    await _seed_person_with_alias(db, "ada@example.com", "ada-alt@example.org")

    with patch("volunteer_call_api.routes.auth.send_email") as send:
        resp = await client.post("/api/auth/login", json={"email": "ada-alt@example.org"})

    assert resp.status_code == 200, resp.text
    assert resp.json()["message"] == "Magic link sent!"
    assert send.called


@pytest.mark.asyncio
async def test_login_by_alias_sends_link_to_typed_address(
    client: AsyncClient, db: AsyncSession
) -> None:
    await _seed_person_with_alias(db, "ada@example.com", "ada-alt@example.org")

    with patch("volunteer_call_api.routes.auth.send_email") as send:
        await client.post("/api/auth/login", json={"email": "ada-alt@example.org"})

    assert send.call_args.kwargs["to"] == "ada-alt@example.org"


@pytest.mark.asyncio
async def test_primary_login_is_case_insensitive(client: AsyncClient, db: AsyncSession) -> None:
    person = Person(
        first_name="Mixed", last_name="Case", email="Mixed.Case@Example.com", active=True
    )
    db.add(person)
    await db.commit()

    with patch("volunteer_call_api.routes.auth.send_email") as send:
        resp = await client.post("/api/auth/login", json={"email": "mixed.case@example.com"})

    assert resp.status_code == 200, resp.text
    assert send.call_args.kwargs["to"] == "mixed.case@example.com"


@pytest.mark.asyncio
async def test_alias_email_globally_unique(db: AsyncSession) -> None:
    p1 = Person(first_name="P", last_name="One", email="p1@example.com", active=True)
    p2 = Person(first_name="P", last_name="Two", email="p2@example.com", active=True)
    db.add_all([p1, p2])
    await db.flush()
    db.add(PersonLoginAlias(person_id=p1.id, email="shared@example.org"))
    await db.commit()

    db.add(PersonLoginAlias(person_id=p2.id, email="shared@example.org"))
    with pytest.raises(IntegrityError):
        await db.commit()


@pytest.mark.asyncio
async def test_unknown_email_still_rejected(client: AsyncClient) -> None:
    resp = await client.post("/api/auth/login", json={"email": "nobody@example.com"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No account found for that email."
