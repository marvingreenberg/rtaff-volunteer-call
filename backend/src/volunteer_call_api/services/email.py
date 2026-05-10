"""Email service — sends via SMTP (Mailpit in dev) or prints to console."""

import logging
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from importlib.resources import files

from volunteer_call_api.config import settings

logger = logging.getLogger(__name__)


# Inline images shared by all templated emails. Keyed by CID (referenced as
# `cid:<key>` in HTML), values are (asset filename, MIME subtype).
INLINE_ASSETS: dict[str, tuple[str, str]] = {
    "rtaff-logo": ("rtaff-logo.png", "png"),
    "tools-image": ("tools-image.jpg", "jpeg"),
}


def _load_asset(filename: str) -> bytes:
    return (files("volunteer_call_api.templates.assets") / filename).read_bytes()


def send_email(
    to: str,
    subject: str,
    html_body: str,
    headers: dict[str, str] | None = None,
    inline_images: list[str] | None = None,
) -> None:
    """Send an email via SMTP. Default config points to Mailpit on port 1025.

    `inline_images` is a list of CID keys from INLINE_ASSETS; each is attached
    as an inline `multipart/related` part so the HTML can reference `cid:<key>`.
    """
    if settings.smtp_host == "console":
        print("\n=== EMAIL (console mode) ===")
        print(f"To: {to}")
        print(f"Subject: {subject}")
        if headers:
            for k, v in headers.items():
                print(f"{k}: {v}")
        if inline_images:
            print(f"Inline images: {', '.join(inline_images)}")
        print(f"Body:\n{html_body}")
        print("=== END EMAIL ===\n")
        return

    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(html_body, "html"))

    if inline_images:
        outer = MIMEMultipart("related")
        outer.attach(alternative)
        for cid in inline_images:
            filename, subtype = INLINE_ASSETS[cid]
            img = MIMEImage(_load_asset(filename), _subtype=subtype)
            img.add_header("Content-ID", f"<{cid}>")
            img.add_header("Content-Disposition", "inline", filename=filename)
            outer.attach(img)
        msg: MIMEMultipart = outer
    else:
        msg = alternative

    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    if headers:
        for k, v in headers.items():
            msg[k] = v

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.send_message(msg)

    logger.info("Email sent to %s: %s", to, subject)
