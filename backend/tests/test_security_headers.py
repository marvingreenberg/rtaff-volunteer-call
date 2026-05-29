"""Tests for default response security headers.

Bugs each test catches:

- ``test_referrer_policy_on_health``: regression where the middleware
  is removed or applied to only a subset of routes — the most likely
  source of a Referer leak is the static-file mount or an error
  response, both of which need the header just as much as JSON
  endpoints.
- ``test_x_content_type_options_on_health``: regression where the
  ``nosniff`` companion header is dropped, opening an MIME-confusion
  vector on user-uploaded content if any ever lands.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from volunteer_call_api.main import app


@pytest.mark.asyncio
async def test_referrer_policy_on_health() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("referrer-policy") == "no-referrer-when-downgrade"


@pytest.mark.asyncio
async def test_x_content_type_options_on_health() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/health")
    assert resp.headers.get("x-content-type-options") == "nosniff"
