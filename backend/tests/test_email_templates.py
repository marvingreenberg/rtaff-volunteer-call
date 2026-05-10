"""Tests for templated emails: inline-image MIME structure and template content."""

import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from volunteer_call_api.services.email import send_email
from volunteer_call_api.services.notifications import (
    EMAIL_INLINE_IMAGES,
    _format_date,
    _format_time_range,
    _full_address,
    task_view,
)

# --- send_email inline-image MIME structure ---


@patch("volunteer_call_api.services.email.settings")
@patch("volunteer_call_api.services.email.smtplib.SMTP")
def test_send_email_inline_images_builds_multipart_related(
    mock_smtp_class: MagicMock, mock_settings: MagicMock
) -> None:
    """With inline_images, the outer container is multipart/related and an
    image part with the requested Content-ID is attached. This is what makes
    `<img src="cid:rtaff-logo">` actually render in mail clients instead of
    showing a broken-image placeholder."""
    mock_settings.smtp_host = "localhost"
    mock_settings.smtp_port = 1025
    mock_settings.smtp_from = "volunteer@rtaff.org"
    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
    mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

    send_email(
        to="vol@example.com",
        subject="Hi",
        html_body='<img src="cid:rtaff-logo">',
        inline_images=["rtaff-logo"],
    )

    sent = mock_server.send_message.call_args[0][0]
    assert sent.get_content_type() == "multipart/related"

    image_parts = [p for p in sent.walk() if p.get_content_type().startswith("image/")]
    assert len(image_parts) == 1
    # email lib stores Content-ID with angle brackets.
    assert image_parts[0]["Content-ID"] == "<rtaff-logo>"


@patch("volunteer_call_api.services.email.settings")
@patch("volunteer_call_api.services.email.smtplib.SMTP")
def test_send_email_no_inline_images_stays_multipart_alternative(
    mock_smtp_class: MagicMock, mock_settings: MagicMock
) -> None:
    """When no inline_images are passed, we don't pay the wrapper cost — the
    message stays a plain multipart/alternative. Catches a regression where
    summary-mode SMS-like emails would still get image attachments."""
    mock_settings.smtp_host = "localhost"
    mock_settings.smtp_port = 1025
    mock_settings.smtp_from = "volunteer@rtaff.org"
    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
    mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

    send_email(to="vol@example.com", subject="Hi", html_body="<p>Hi</p>")

    sent = mock_server.send_message.call_args[0][0]
    assert sent.get_content_type() == "multipart/alternative"


def test_email_inline_images_constant_matches_template_cids() -> None:
    """The CID list passed to send_email must match what the base template
    references; otherwise images render as broken in every email."""
    assert EMAIL_INLINE_IMAGES == ["rtaff-logo", "tools-image"]


# --- task_view formatting ---


def _task(
    *,
    short_description: str = "Replace ceiling fan",
    date: datetime.date | None = datetime.date(2026, 5, 16),
    time_start: datetime.time | None = datetime.time(9, 0),
    time_end: datetime.time | None = datetime.time(13, 0),
    address: str | None = "123 Main St",
    city: str | None = "Arlington, VA",
    team_lead: object | None = None,
    notes: str | None = None,
) -> object:
    return SimpleNamespace(
        short_description=short_description,
        date=date,
        time_start=time_start,
        time_end=time_end,
        address=address,
        city=city,
        team_lead=team_lead,
        notes=notes,
    )


def test_task_view_summary_omits_full_details() -> None:
    """The invite email gets the summary view — including full address there
    would leak homeowner addresses to every volunteer regardless of
    assignment, which is exactly what we don't want."""
    view = task_view(_task(), include_full_details=False)
    assert "full_address" not in view
    assert "team_lead" not in view
    assert "time_label" not in view
    assert view["city"] == "Arlington, VA"


def test_task_view_full_includes_address_time_lead_notes() -> None:
    lead = SimpleNamespace(
        first_name="Pat", last_name="Lee", phone="555-1212", email="pat@example.com"
    )
    view = task_view(_task(team_lead=lead, notes="Bring ladder"), include_full_details=True)
    assert view["full_address"] == "123 Main St\nArlington, VA"
    assert view["team_lead"] == {
        "name": "Pat Lee",
        "phone": "555-1212",
        "email": "pat@example.com",
    }
    assert view["time_label"] == "9:00 AM – 1:00 PM"
    assert view["notes"] == "Bring ladder"


def test_format_date_handles_missing() -> None:
    assert _format_date(None) == "Date TBD"
    assert "May" in _format_date(datetime.date(2026, 5, 16))


def test_format_time_range_endpoints() -> None:
    assert _format_time_range(None, None) is None
    assert _format_time_range(datetime.time(9, 0), None) == "9:00 AM"
    assert _format_time_range(datetime.time(9, 0), datetime.time(13, 30)) == "9:00 AM – 1:30 PM"


def test_full_address_combines_address_and_city() -> None:
    assert (
        _full_address(_task(address="1 X St", city="Falls Church, VA"))
        == "1 X St\nFalls Church, VA"
    )
    assert _full_address(_task(address=None, city="Falls Church, VA")) == "Falls Church, VA"
    assert _full_address(_task(address="1 X St", city=None)) == "1 X St"
    assert _full_address(_task(address=None, city=None)) is None


# --- Template rendering: assignment email contains address + team lead + link ---


def _render_assignment_template() -> str:
    from volunteer_call_api.services.notifications import _jinja_env

    template = _jinja_env.get_template("volunteer_assignment.html")
    lead = SimpleNamespace(
        first_name="Pat", last_name="Lee", phone="555-1212", email="pat@example.com"
    )
    tasks = [
        task_view(
            _task(
                short_description="Replace ceiling fan",
                team_lead=lead,
                notes="Bring ladder",
            ),
            include_full_details=True,
        )
    ]
    return template.render(
        subject="Your assignments for May 16",
        title="May 16 Repair Day",
        subtitle="You're confirmed for 1 task",
        first_name="Sam",
        tasks=tasks,
        volunteering_url="https://app.example.com/volunteering?token=abc",
    )


def test_assignment_template_includes_address_team_lead_and_link() -> None:
    """All three are explicit user requirements — if any of these regress,
    the email loses the information volunteers need on the day of the job."""
    html = _render_assignment_template()
    assert "123 Main St" in html
    assert "Arlington, VA" in html
    assert "Pat Lee" in html
    assert "555-1212" in html
    assert "pat@example.com" in html
    assert "Bring ladder" in html
    assert 'href="https://app.example.com/volunteering?token=abc"' in html


def test_assignment_template_omits_team_lead_section_when_absent() -> None:
    """When team_lead isn't populated yet (early in the program lifecycle),
    we should silently drop the section, not render an empty 'Team lead:' label."""
    from volunteer_call_api.services.notifications import _jinja_env

    template = _jinja_env.get_template("volunteer_assignment.html")
    tasks = [task_view(_task(team_lead=None, notes=None), include_full_details=True)]
    html = template.render(
        subject="x",
        title="x",
        subtitle=None,
        first_name="Sam",
        tasks=tasks,
        volunteering_url="https://app.example.com/v?token=z",
    )
    assert "Team lead" not in html
    assert "Notes:" not in html


def test_invite_template_includes_task_list_and_link() -> None:
    from volunteer_call_api.services.notifications import _jinja_env

    template = _jinja_env.get_template("volunteer_invite.html")
    tasks = [
        task_view(_task(short_description="Repair porch railing"), include_full_details=False),
        task_view(
            _task(short_description="Install grab bars", date=datetime.date(2026, 5, 23)),
            include_full_details=False,
        ),
    ]
    html = template.render(
        subject="Volunteer Call: May",
        title="May Repair Days",
        subtitle="2 tasks need volunteers",
        first_name="Sam",
        call_title="May Repair Days",
        tasks=tasks,
        volunteering_url="https://app.example.com/volunteering?token=abc",
    )
    assert "Repair porch railing" in html
    assert "Install grab bars" in html
    # Invite must NOT leak full street address.
    assert "123 Main St" not in html
    assert 'href="https://app.example.com/volunteering?token=abc"' in html
