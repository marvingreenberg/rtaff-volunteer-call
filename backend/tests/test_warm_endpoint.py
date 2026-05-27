"""Tests for the /warm endpoint used by the Cloud Run scheduled warmer.

Bugs each test catches:

- ``test_warm_endpoint_returns_warm``: regression where someone
  refactors /health and /warm together and silently changes /warm's
  shape — Cloud Scheduler treats any 2xx as success so the symptom
  would be a misnamed endpoint.
- ``test_warm_endpoint_no_auth_required``: regression where a future
  blanket-auth middleware accidentally locks the warmer out, killing
  the keep-warm path and reintroducing cold starts.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from volunteer_call_api.main import app


@pytest.mark.asyncio
async def test_warm_endpoint_returns_warm() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/warm")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "warm"
    assert "version" in body


@pytest.mark.asyncio
async def test_warm_endpoint_no_auth_required() -> None:
    # No cookies, no headers — must still 200. Cloud Scheduler doesn't
    # know about JWTs.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/warm")
    assert resp.status_code == 200
