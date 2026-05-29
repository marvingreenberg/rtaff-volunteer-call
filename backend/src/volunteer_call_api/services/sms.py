"""SMS service — stub provider.

For now ``send_sms`` logs the outbound message instead of hitting a real
provider. The call sites in :mod:`volunteer_call_api.services.notifications`
are real — wiring is in place so a future Twilio / MessageBird / etc.
adapter can be dropped in without touching callers.

Toggle behavior via ``settings.sms_provider``:

- ``"stub"`` (default): log a structured ``[SMS stub]`` line at INFO and
  return. Safe in tests and dev — no provider required.
- ``"disabled"``: log at DEBUG and return. For local dev when even the
  log noise is unwanted.
"""

import logging

from volunteer_call_api.config import settings

logger = logging.getLogger(__name__)


def send_sms(to: str, body: str) -> None:
    """Send an SMS through the configured provider stub."""
    provider = settings.sms_provider
    if provider == "disabled":
        logger.debug("SMS suppressed (provider=disabled) to=%s", to)
        return
    # "stub" is the default; anything else falls through with a warning
    # so an accidental misconfiguration is visible but not fatal.
    if provider != "stub":
        logger.warning("Unknown sms_provider=%r; falling back to stub behavior.", provider)
    # One line, kv pairs, so it greps cleanly in production logs.
    logger.info("[SMS stub] to=%s body=%s", to, body.replace("\n", " | "))
