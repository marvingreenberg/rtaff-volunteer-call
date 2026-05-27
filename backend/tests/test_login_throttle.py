"""Tests for login brute-force throttle."""

import time
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from volunteer_call_api.database import get_db
from volunteer_call_api.main import app
from volunteer_call_api.models import Base, Person
from volunteer_call_api.services.login_throttle import LoginThrottle, login_throttle
from volunteer_call_api.services.tokens import issue_login_token

# ---------------------------------------------------------------------------
# Unit tests for LoginThrottle
# ---------------------------------------------------------------------------


class TestLoginThrottle:
    def test_initial_state(self) -> None:
        t = LoginThrottle(threshold=3, base_window=60)
        assert not t.is_throttled
        assert t.invalid_count == 0
        assert t.escalation_level == 1

    def test_below_threshold_not_throttled(self) -> None:
        t = LoginThrottle(threshold=5, base_window=60)
        for _ in range(4):
            t.record_invalid()
        assert not t.is_throttled

    def test_reaching_threshold_triggers_throttle(self) -> None:
        t = LoginThrottle(threshold=3, base_window=60)
        for _ in range(3):
            t.record_invalid()
        assert t.is_throttled
        assert t.invalid_count == 0  # reset after entering throttle

    def test_throttle_expires_after_window(self) -> None:
        t = LoginThrottle(threshold=2, base_window=10)
        t.record_invalid()
        t.record_invalid()
        assert t.is_throttled

        with patch("volunteer_call_api.services.login_throttle.time") as mock_time:
            mock_time.time.return_value = time.time() + 11
            assert not t.is_throttled
            assert t.escalation_level == 1

    def test_escalation_doubles_window(self) -> None:
        t = LoginThrottle(threshold=2, base_window=60)
        # First batch triggers throttle
        t.record_invalid()
        t.record_invalid()
        assert t.is_throttled
        assert t.current_window == 60

        # Second batch while throttled doubles it
        t.record_invalid()
        t.record_invalid()
        assert t.current_window == 120
        assert t.escalation_level == 2

    def test_double_escalation(self) -> None:
        t = LoginThrottle(threshold=2, base_window=60)
        for _ in range(2):
            t.record_invalid()
        assert t.escalation_level == 1
        for _ in range(2):
            t.record_invalid()
        assert t.escalation_level == 2
        for _ in range(2):
            t.record_invalid()
        assert t.escalation_level == 4
        assert t.current_window == 240

    def test_reset_clears_state(self) -> None:
        t = LoginThrottle(threshold=2, base_window=10)
        t.record_invalid()
        t.record_invalid()
        assert t.is_throttled
        t._reset()
        assert not t.is_throttled
        assert t.escalation_level == 1
        assert t.invalid_count == 0


# ---------------------------------------------------------------------------
# Integration tests for the login endpoint with throttling
# ---------------------------------------------------------------------------


@pytest.fixture
async def throttle_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def throttle_db(throttle_engine) -> AsyncSession:
    factory = async_sessionmaker(throttle_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def throttle_client(throttle_engine) -> AsyncClient:
    factory = async_sessionmaker(throttle_engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    # Reset throttle state before each test
    login_throttle._reset()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    login_throttle._reset()


@pytest.mark.asyncio
async def test_normal_mode_404_for_unknown_email(throttle_client: AsyncClient) -> None:
    resp = await throttle_client.post("/api/auth/login", json={"email": "bad@example.com"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No account found for that email."


@pytest.mark.asyncio
async def test_throttle_activates_after_threshold(throttle_client: AsyncClient) -> None:
    # Use a low threshold for testing
    original_threshold = login_throttle.threshold
    login_throttle.threshold = 3
    try:
        for i in range(2):
            resp = await throttle_client.post(
                "/api/auth/login", json={"email": f"bad{i}@example.com"}
            )
            assert resp.status_code == 404

        # Third invalid triggers throttle — but this attempt itself is still in normal mode
        # when it starts, then record_invalid triggers throttle
        resp = await throttle_client.post("/api/auth/login", json={"email": "bad2@example.com"})
        assert resp.status_code == 404

        # Now throttled — next invalid should get 200 generic
        resp = await throttle_client.post("/api/auth/login", json={"email": "bad3@example.com"})
        assert resp.status_code == 200
        assert "If bad3@example.com is registered" in resp.json()["message"]
    finally:
        login_throttle.threshold = original_threshold


@pytest.mark.asyncio
async def test_valid_email_in_throttled_mode_sends_email_generic_message(
    throttle_client: AsyncClient, throttle_db: AsyncSession
) -> None:
    person = Person(first_name="Alice", last_name="Test", email="alice@example.com", active=True)
    throttle_db.add(person)
    await throttle_db.commit()

    # Force throttle on
    login_throttle.throttle_start = time.time()
    login_throttle.escalation_level = 1

    resp = await throttle_client.post("/api/auth/login", json={"email": "alice@example.com"})
    assert resp.status_code == 200
    assert "If alice@example.com is registered" in resp.json()["message"]
    # Person row remains untouched — there's no per-person token to persist now.
    await throttle_db.refresh(person)
    assert person.active is True


@pytest.mark.asyncio
async def test_verify_magic_link_serializes_full_person(
    throttle_client: AsyncClient, throttle_db: AsyncSession
) -> None:
    """Bug it catches: auth.verify_magic_link loaded Person with
    selectinload(Person.roles) only, but _person_response also touches
    program_memberships. Under asyncpg this triggered MissingGreenlet at
    request time. Under sqlite the lazy-load works silently — but the
    serializer still must not blow up, so this test guards against
    regressing the eager-load options."""
    from volunteer_call_api.models.person import (
        PersonRole,
        Program,
        RoleType,
        VolunteerProgram,
    )

    person = Person(
        first_name="Vera",
        last_name="Verifier",
        email="vera@example.com",
        active=True,
    )
    throttle_db.add(person)
    await throttle_db.flush()
    throttle_db.add(PersonRole(person_id=person.id, role=RoleType.VOLUNTEER))
    throttle_db.add(VolunteerProgram(person_id=person.id, program=Program.RTX))
    await throttle_db.commit()

    token = issue_login_token(person.id)
    resp = await throttle_client.post("/api/auth/verify", json={"token": token})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["invited_call_id"] is None
    serialized = body["person"]
    assert serialized["id"] == person.id
    # Both relationships must be present, proving they were eager-loaded.
    assert "volunteer" in serialized["roles"]
    assert any(m["program"] == "RTX" for m in serialized["programs"])
    # And the bearer secret must not have leaked.
    assert "calendar_url" not in serialized
    # The HttpOnly session cookie must have been set on the response.
    cookie_header = resp.headers.get("set-cookie", "")
    assert "session=" in cookie_header
    assert "HttpOnly" in cookie_header


@pytest.mark.asyncio
async def test_valid_email_normal_mode_personalized_message(
    throttle_client: AsyncClient, throttle_db: AsyncSession
) -> None:
    person = Person(first_name="Bob", last_name="Test", email="bob@example.com", active=True)
    throttle_db.add(person)
    await throttle_db.commit()

    resp = await throttle_client.post("/api/auth/login", json={"email": "bob@example.com"})
    assert resp.status_code == 200
    assert resp.json()["message"] == "Magic link sent!"
