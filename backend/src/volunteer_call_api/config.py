"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_url: str = (
        "postgresql+asyncpg://volunteer_call:volunteer_call_dev@localhost:5432/volunteer_call"
    )

    # SMTP — defaults point to Mailpit (dev) on port 1025.
    # Set smtp_host=console to print emails to stdout instead.
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "volunteer@rtaff.org"

    app_base_url: str = "http://localhost:5173"

    # Secret for signing magic-link / invite JWTs (HS256). MUST be overridden
    # in production via env var. The dev default is fine for local work but
    # tokens issued against it are obviously not safe to ship.
    jwt_secret: str = "dev-jwt-secret-change-me"
    # Login magic links are short-lived: they only need to survive the
    # round-trip from inbox to first click. Once verified, a separate,
    # longer-lived session token (below) is minted for the cookie.
    jwt_login_ttl_minutes: int = 10
    # Invite links are emailed about a specific call and may be clicked
    # days after they're sent, so they keep a longer lifetime.
    jwt_invite_ttl_days: int = 14
    # Lifetime of the session token stored in the HttpOnly cookie after a
    # successful magic-link/invite verification. Decoupled from the link
    # TTLs so shortening a magic link doesn't shorten the session.
    jwt_session_ttl_days: int = 14

    # SMS provider. "stub" logs the outbound message; "disabled" silently
    # drops it. Real provider integration (Twilio etc.) will land as a
    # new value here.
    sms_provider: str = "stub"

    # Demo mode: skip the magic-link email step and return the access token
    # directly in the /login response. For local demos only.
    demo_mode: bool = False

    # Toggle for the double-submit-cookie CSRF middleware. On in prod and
    # dev; the test suite turns it off via conftest so existing
    # state-change tests don't have to thread a CSRF header through every
    # POST. The middleware logic itself is exercised by tests/test_csrf.py.
    csrf_enabled: bool = True

    model_config = {"env_file": ".env"}


settings = Settings()
