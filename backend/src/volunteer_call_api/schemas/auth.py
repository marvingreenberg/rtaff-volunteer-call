from pydantic import BaseModel, EmailStr


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
