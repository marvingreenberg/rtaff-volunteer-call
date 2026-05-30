from pydantic import BaseModel, EmailStr

from volunteer_call_api.schemas.person import PersonResponse


class LoginRequest(BaseModel):
    """Schema for requesting a magic link login."""

    email: EmailStr


class LoginResponse(BaseModel):
    """Schema for response after requesting magic link."""

    message: str
    # Populated only when DEMO_MODE is enabled. Lets the client skip the
    # email round-trip and verify directly. Never set in production.
    demo_token: str | None = None


class VerifyRequest(BaseModel):
    """Schema for verifying a magic link token."""

    token: str


class AuthContextResponse(BaseModel):
    """Current-auth context: the person plus any invite deep-link target.

    Returned by both ``POST /auth/verify`` and ``GET /auth/me`` so the two
    endpoints share one shape. ``invited_call_id`` is set when the
    presented token was an *invite* token (minted by a volunteer-call
    invite email); the frontend uses it to deep-link to that call on the
    /volunteering page. It is ``None`` for login/session tokens.
    """

    person: PersonResponse
    invited_call_id: str | None = None


# The verify endpoint keeps its descriptive name; same shape.
VerifyResponse = AuthContextResponse
