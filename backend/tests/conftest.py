"""Pytest fixtures for volunteer_call_api tests."""

import os

os.environ.setdefault("SMTP_HOST", "console")

import pytest
from httpx import ASGITransport, AsyncClient

from volunteer_call_api.dependencies import get_current_user
from volunteer_call_api.main import app
from volunteer_call_api.models.person import Person


def _stub_user() -> Person:
    return Person(first_name="Test", last_name="User", active=True)


@pytest.fixture
async def client() -> AsyncClient:
    """Async HTTP client for testing the API."""
    app.dependency_overrides[get_current_user] = _stub_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)
