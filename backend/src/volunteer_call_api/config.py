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

    # Demo mode: skip the magic-link email step and return the access token
    # directly in the /login response. For local demos only.
    demo_mode: bool = False

    model_config = {"env_file": ".env"}


settings = Settings()
