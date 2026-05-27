"""Signed-JWT auth tokens.

Two token shapes share one signing key:

- ``login`` — issued by ``POST /auth/login``; carries only the person id.
- ``invite`` — issued when a volunteer call's invites go out; carries
  ``person_id`` and ``call_id`` so the frontend can deep-link to the call
  the email was about.

The token is the credential. There is no DB-side state — verification is
purely a signature check plus an expiry check, so revocation is bounded
by the TTL (default 14 days, see ``settings.jwt_ttl_days``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt

from volunteer_call_api.config import settings

ALGORITHM = "HS256"

TokenType = Literal["login", "invite"]


class TokenError(Exception):
    """Base for token decode failures."""


class TokenExpired(TokenError):
    """Token signature was valid but the token is past its ``exp``."""


class TokenInvalid(TokenError):
    """Signature failed, claims were malformed, or ``typ`` didn't match."""


@dataclass(frozen=True)
class TokenClaims:
    """Decoded token claims, normalized for callers."""

    person_id: str
    token_type: TokenType
    call_id: str | None
    issued_at: datetime
    expires_at: datetime


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _issue(payload: dict[str, object], ttl: timedelta | None) -> str:
    now = _now()
    exp = now + (ttl if ttl is not None else timedelta(days=settings.jwt_ttl_days))
    payload = {**payload, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def issue_login_token(person_id: str, ttl: timedelta | None = None) -> str:
    """Token for the email-magic-link login flow. No call binding."""
    return _issue({"sub": person_id, "typ": "login"}, ttl)


def issue_invite_token(person_id: str, call_id: str, ttl: timedelta | None = None) -> str:
    """Token for a volunteer-call invite email. Carries the call id."""
    return _issue({"sub": person_id, "typ": "invite", "call_id": call_id}, ttl)


def decode_token(token: str) -> TokenClaims:
    """Verify signature + expiry; return normalized claims.

    Raises :class:`TokenExpired` when the token is past ``exp`` and
    :class:`TokenInvalid` for any other failure (bad signature, missing
    fields, unknown ``typ``).
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as e:
        raise TokenExpired("Token has expired") from e
    except jwt.InvalidTokenError as e:
        raise TokenInvalid(f"Invalid token: {e}") from e

    sub = payload.get("sub")
    typ = payload.get("typ")
    if not isinstance(sub, str) or typ not in ("login", "invite"):
        raise TokenInvalid("Missing or invalid sub/typ")

    call_id = payload.get("call_id")
    if typ == "invite":
        if not isinstance(call_id, str):
            raise TokenInvalid("invite token missing call_id")
    else:
        call_id = None

    return TokenClaims(
        person_id=sub,
        token_type=typ,
        call_id=call_id,
        issued_at=datetime.fromtimestamp(int(payload["iat"]), tz=timezone.utc),
        expires_at=datetime.fromtimestamp(int(payload["exp"]), tz=timezone.utc),
    )
