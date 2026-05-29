"""Tests for the double-submit-cookie CSRF middleware.

Bugs each test catches:

- ``test_get_sets_csrf_cookie``: regression where the middleware
  forgets to mint a csrf cookie on a fresh client — the frontend
  can never write because it has nothing to echo in the header.
- ``test_post_without_token_rejected``: regression where the
  middleware short-circuits on missing header and lets the write
  through — the bare-minimum CSRF guarantee.
- ``test_post_with_mismatched_token_rejected``: regression where
  the comparison is loose (e.g. always-true on truthy header) and
  any value satisfies the check.
- ``test_post_with_matching_token_passes``: regression where the
  guard rejects even legitimate writes from the frontend.
- ``test_login_exempt_from_csrf``: regression where the login
  bootstrap is gated on CSRF, breaking the very first request a
  brand-new browser ever makes.
- ``test_verify_exempt_from_csrf``: same logic — verify is gated
  by the JWT signature, not by CSRF.
- ``test_safe_methods_not_gated``: regression where GET/HEAD start
  requiring the header, breaking every read.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from volunteer_call_api.config import settings
from volunteer_call_api.database import get_db
from volunteer_call_api.main import app
from volunteer_call_api.models import Base


@pytest.fixture(autouse=True)
def _enable_csrf():  # type: ignore[no-untyped-def]
    """Re-enable CSRF for this file only; the global conftest disables it."""
    settings.csrf_enabled = True
    yield
    settings.csrf_enabled = False


@pytest.fixture
async def client() -> AsyncClient:
    """Client with an in-memory aiosqlite DB.

    The CSRF tests only need the route to reach (or not reach) its
    business logic — they don't care what the DB returns. Without an
    override the login-exempt test would try the configured Postgres
    URL and OSError when nothing's running locally.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():  # type: ignore[no-untyped-def]
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_sets_csrf_cookie(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    # cookie is set on the response — httpx jars it on the client.
    assert "csrf" in client.cookies


@pytest.mark.asyncio
async def test_safe_methods_not_gated(client: AsyncClient) -> None:
    # GET on a protected route returns its normal 401 (no auth) — not 403 CSRF.
    resp = await client.get("/api/auth/me")
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_post_without_token_rejected(client: AsyncClient) -> None:
    # Prime cookies first so we have a real csrf cookie sitting in the jar.
    await client.get("/health")
    # Send a POST without the X-CSRF-Token header — should 403.
    resp = await client.post(
        "/api/people/some-id/calendar",
        json={"calendar_url": "https://x"},
    )
    assert resp.status_code == 403
    assert "CSRF" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_post_with_mismatched_token_rejected(client: AsyncClient) -> None:
    await client.get("/health")
    resp = await client.post(
        "/api/people/some-id/calendar",
        json={"calendar_url": "https://x"},
        headers={"X-CSRF-Token": "not-the-cookie-value"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_post_with_matching_token_passes_csrf_check(
    client: AsyncClient,
) -> None:
    await client.get("/health")
    cookie = client.cookies.get("csrf")
    assert cookie is not None
    # CSRF should accept; downstream may still reject for other reasons
    # (auth, validation) — we only assert it isn't a 403 from CSRF.
    resp = await client.post(
        "/api/people/some-id/calendar",
        json={"calendar_url": "https://x"},
        headers={"X-CSRF-Token": cookie},
    )
    assert resp.status_code != 403 or "CSRF" not in resp.json().get("detail", "")


@pytest.mark.asyncio
async def test_login_exempt_from_csrf(client: AsyncClient) -> None:
    # No csrf cookie, no header — login must still work (or reach the
    # business logic, which will 404 on unknown email).
    resp = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com"},
    )
    # Anything but 403 means CSRF didn't block it.
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_verify_exempt_from_csrf(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/verify",
        json={"token": "not-a-real-token"},
    )
    # 401 (bad token) is the expected outcome; 403 would mean CSRF tripped.
    assert resp.status_code != 403
