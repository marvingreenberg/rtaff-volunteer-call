"""Authentication services for token-based volunteer identity."""

import secrets


def generate_access_token() -> str:
    """Generate a URL-safe access token for volunteer self-service links."""
    return secrets.token_urlsafe(32)
