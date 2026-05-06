"""Tests for email service and send-invites schema."""

from unittest.mock import MagicMock, patch

from volunteer_call_api.schemas.volunteer_call import SendInvitesResponse
from volunteer_call_api.services.email import send_email


@patch("volunteer_call_api.services.email.settings")
def test_send_email_console_mode(mock_settings: MagicMock) -> None:
    """In console mode, send_email logs instead of sending."""
    mock_settings.smtp_host = "console"
    send_email(to="test@example.com", subject="Test", html_body="<p>Hello</p>")


@patch("volunteer_call_api.services.email.settings")
@patch("volunteer_call_api.services.email.smtplib.SMTP")
def test_send_email_smtp_mode(mock_smtp_class: MagicMock, mock_settings: MagicMock) -> None:
    """In SMTP mode, send_email connects and sends via SMTP."""
    mock_settings.smtp_host = "localhost"
    mock_settings.smtp_port = 1025
    mock_settings.smtp_from = "volunteer@rtaff.org"

    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
    mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

    send_email(to="vol@example.com", subject="Invite", html_body="<p>Come help</p>")

    mock_smtp_class.assert_called_once_with("localhost", 1025)
    mock_server.send_message.assert_called_once()


@patch("volunteer_call_api.services.email.settings")
@patch("volunteer_call_api.services.email.smtplib.SMTP")
def test_send_email_with_headers(mock_smtp_class: MagicMock, mock_settings: MagicMock) -> None:
    """Custom headers (e.g. List-Unsubscribe) are added to the message."""
    mock_settings.smtp_host = "localhost"
    mock_settings.smtp_port = 1025
    mock_settings.smtp_from = "volunteer@rtaff.org"

    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
    mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

    send_email(
        to="vol@example.com",
        subject="Call",
        html_body="<p>Hi</p>",
        headers={"List-Unsubscribe": "<http://example.com/unsub>"},
    )

    mock_server.send_message.assert_called_once()
    sent_msg = mock_server.send_message.call_args[0][0]
    assert sent_msg["List-Unsubscribe"] == "<http://example.com/unsub>"


def test_send_invites_response_schema() -> None:
    resp = SendInvitesResponse(volunteers_notified=5, volunteers_skipped=2)
    assert resp.volunteers_notified == 5
    assert resp.volunteers_skipped == 2


def test_send_invites_response_zero() -> None:
    resp = SendInvitesResponse(volunteers_notified=0, volunteers_skipped=0)
    assert resp.volunteers_notified == 0
