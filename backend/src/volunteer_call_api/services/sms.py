"""SMS service — console-only for dev, production providers deferred."""

import logging

logger = logging.getLogger(__name__)


def send_sms(to: str, body: str) -> None:
    """Send an SMS. Currently prints to console; Twilio integration deferred."""
    print("\n=== SMS (console mode) ===")
    print(f"To: {to}")
    print(f"Body: {body}")
    print("=== END SMS ===\n")
    logger.info("SMS (console) sent to %s", to)
