"""FastAPI application entry point."""

import importlib.metadata
import logging
import os
import secrets
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from volunteer_call_api.routes import api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:     %(name)s - %(message)s",
)

_version = importlib.metadata.version("volunteer-call-api")

app = FastAPI(
    title="RT-AFF Volunteer Call API",
    description="Volunteer Call Notification System for RT-AFF",
    version=_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("CORS_ORIGIN", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Default security headers applied to every response.

    Referrer-Policy: ``no-referrer-when-downgrade`` keeps URL-embedded
    magic-link / invite tokens from leaking via Referer when a user
    navigates to a less-secure (http) origin. Set here rather than
    per-route so every endpoint — including the static file mount —
    gets the same treatment.

    X-Content-Type-Options: ``nosniff`` is the obvious companion and
    free to add while we're here.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("Referrer-Policy", "no-referrer-when-downgrade")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        return response


# Endpoints exempt from CSRF — login is the bootstrap (no session yet),
# verify uses a signed JWT that itself functions as the CSRF token.
CSRF_EXEMPT_PATHS = {"/api/auth/login", "/api/auth/verify", "/api/auth/logout"}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit-cookie CSRF guard.

    On every request, ensure a ``csrf`` cookie is set (non-HttpOnly so JS
    can read it). On state-changing requests (POST/PUT/PATCH/DELETE)
    that aren't exempt, require the request to carry an ``X-CSRF-Token``
    header whose value equals the cookie. The header lookup means a
    cross-site form submission — which can't read the cookie — can't
    forge the header, defeating the classic CSRF vector even with
    SameSite=Lax not blocking the request itself.

    The login/verify routes are exempt because (1) login has no session
    yet, and (2) verify itself only accepts a signed JWT that an
    attacker can't mint.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Import inside the method so test-time changes to settings.csrf_enabled
        # are picked up without re-importing main.
        from volunteer_call_api.config import settings as runtime_settings

        if not runtime_settings.csrf_enabled:
            return await call_next(request)

        csrf_cookie = request.cookies.get("csrf")
        new_cookie: str | None = None
        if csrf_cookie is None:
            new_cookie = secrets.token_urlsafe(32)
            csrf_cookie = new_cookie

        if (
            request.method not in SAFE_METHODS
            and request.url.path not in CSRF_EXEMPT_PATHS
            and request.url.path.startswith("/api/")
        ):
            header_value = request.headers.get("x-csrf-token")
            if not header_value or not secrets.compare_digest(header_value, csrf_cookie):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF token missing or invalid"},
                )

        response = await call_next(request)
        if new_cookie is not None:
            response.set_cookie(
                key="csrf",
                value=new_cookie,
                max_age=60 * 60 * 24 * 14,
                httponly=False,  # JS must read it to echo in the header
                secure=request.url.scheme == "https",
                samesite="lax",
                path="/",
            )
        return response


# Order matters: outermost middleware first. Security headers wraps
# CSRF (so the headers apply even to CSRF rejections).
app.add_middleware(CSRFMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": _version}


@app.get("/warm")
async def warm_check() -> dict[str, str]:
    """Cold-start avoidance endpoint.

    Hit by Cloud Scheduler on a cron during expected usage windows and
    by the frontend's heartbeat while a session is active. The
    endpoint exists separately from /health so its access pattern
    (high-frequency, tolerates a 5xx without paging) is greppable in
    request logs.
    """
    return {"status": "warm", "version": _version}


static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
