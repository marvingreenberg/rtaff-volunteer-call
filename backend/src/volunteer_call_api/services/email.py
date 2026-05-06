"""Email service — sends via SMTP (Mailpit in dev) or prints to console."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from volunteer_call_api.config import settings

logger = logging.getLogger(__name__)


def send_email(
    to: str,
    subject: str,
    html_body: str,
    headers: dict[str, str] | None = None,
) -> None:
    """Send an email via SMTP. Default config points to Mailpit on port 1025."""
    if settings.smtp_host == "console":
        print("\n=== EMAIL (console mode) ===")
        print(f"To: {to}")
        print(f"Subject: {subject}")
        if headers:
            for k, v in headers.items():
                print(f"{k}: {v}")
        print(f"Body:\n{html_body}")
        print("=== END EMAIL ===\n")
        return

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject

    if headers:
        for k, v in headers.items():
            msg[k] = v

    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.send_message(msg)

    logger.info("Email sent to %s: %s", to, subject)
