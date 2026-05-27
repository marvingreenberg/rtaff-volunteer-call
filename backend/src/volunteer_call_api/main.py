"""FastAPI application entry point."""

import importlib.metadata
import logging
import os
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

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


app.add_middleware(SecurityHeadersMiddleware)

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": _version}


static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
