"""Pytest fixtures for volunteer_call_api tests."""

import os

os.environ.setdefault("SMTP_HOST", "console")

from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient

from volunteer_call_api.config import settings
from volunteer_call_api.dependencies import get_current_user
from volunteer_call_api.main import app
from volunteer_call_api.models.person import Person


def _stub_user() -> Person:
    return Person(first_name="Test", last_name="User", active=True)


@pytest.fixture(autouse=True)
def _pinned_settings() -> Iterator[None]:
    """Pin runtime settings to a deterministic baseline for every test.

    Without this, a test's outcome can depend on whatever env vars happen
    to be exported in the developer's shell (DEMO_MODE, etc.)
    Tests that need a specific mode override the field locally; the
    snapshot restores everything afterward.
    """
    snapshot = settings.model_dump()
    settings.demo_mode = False
    try:
        yield
    finally:
        for k, v in snapshot.items():
            setattr(settings, k, v)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Async HTTP client for testing the API.

    pytest-asyncio is in `asyncio_mode = "auto"` (see pyproject.toml), so
    plain `@pytest.fixture` works on `async def`. Without auto-mode this
    would need `@pytest_asyncio.fixture` — without it, the fixture is
    silently treated as a coroutine and tests get a coroutine instead of
    an AsyncClient.
    """
    app.dependency_overrides[get_current_user] = _stub_user
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_current_user, None)
