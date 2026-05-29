"""Tests for the SMS stub provider and deliver_notification's SMS path.

Bugs each test catches:

- ``test_send_sms_stub_logs_at_info``: regression where the stub
  starts printing to stdout (the original implementation) or stops
  logging entirely — both make CI test output noisy or hide outbound
  SMS in production logs.
- ``test_send_sms_disabled_suppresses_log_at_info``: regression where
  the ``disabled`` setting silently still logs at INFO, defeating
  the "quiet local dev" path.
- ``test_deliver_notification_fires_sms_for_sms_pref``: regression
  where deliver_notification's SMS branch is gated on something other
  than NotificationPreference.SMS / BOTH — the original bug that
  motivated the wiring task in todo.md.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

from volunteer_call_api.config import settings
from volunteer_call_api.models.person import (
    NotificationPreference,
    Person,
    SubscriptionStatus,
)
from volunteer_call_api.services import notifications, sms


def test_send_sms_stub_logs_at_info(caplog) -> None:  # type: ignore[no-untyped-def]
    settings.sms_provider = "stub"
    with caplog.at_level(logging.INFO, logger="volunteer_call_api.services.sms"):
        sms.send_sms(to="+15555550100", body="hello")
    messages = [r.message for r in caplog.records]
    assert any("[SMS stub] to=+15555550100" in m for m in messages)
    assert any("body=hello" in m for m in messages)


def test_send_sms_disabled_suppresses_log_at_info(caplog) -> None:  # type: ignore[no-untyped-def]
    settings.sms_provider = "disabled"
    try:
        with caplog.at_level(logging.INFO, logger="volunteer_call_api.services.sms"):
            sms.send_sms(to="+15555550100", body="hello")
        info_messages = [r.message for r in caplog.records if r.levelno >= logging.INFO]
        assert not any("[SMS stub]" in m for m in info_messages)
    finally:
        settings.sms_provider = "stub"


def test_deliver_notification_fires_sms_for_sms_pref() -> None:
    """SMS-only preference must dispatch through send_sms with the SMS
    body and the link appended."""
    person = Person(
        first_name="P",
        last_name="One",
        email="p@example.com",
        phone="+15555550100",
        active=True,
        notification_preference=NotificationPreference.SMS,
        subscription_status=SubscriptionStatus.ACTIVE,
    )
    with patch.object(notifications, "send_sms") as sms_spy:
        with patch.object(notifications, "send_email") as email_spy:
            delivered = notifications.deliver_notification(
                person=person,
                subject="ignored",
                full_body="full html",
                summary_body="text summary",
                link="/volunteering?token=abc",
            )
    assert delivered is True
    assert email_spy.call_count == 0
    sms_spy.assert_called_once()
    kwargs = sms_spy.call_args.kwargs
    assert kwargs["to"] == "+15555550100"
    assert "text summary" in kwargs["body"]
    assert "/volunteering?token=abc" in kwargs["body"]
