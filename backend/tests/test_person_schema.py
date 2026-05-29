"""Schema invariants. The big one: calendar_url must never escape via PersonResponse."""

import datetime as dt

from volunteer_call_api.models.person import (
    CalendarKind,
    NotificationDetailLevel,
    NotificationPreference,
    PersonCalendar,
    Skill,
    SubscriptionStatus,
)
from volunteer_call_api.routes.people import _person_response
from volunteer_call_api.schemas.person import PersonResponse


class _StubPerson:
    """Minimal duck-typed Person — avoids needing a DB."""

    def __init__(self, **overrides: object) -> None:
        self.id = "p1"
        self.first_name = "Alice"
        self.last_name = "Tester"
        self.email = "alice@example.com"
        self.phone = None
        self.phone_verified = False
        self.skills: list[Skill] = []
        self.active = True
        self.notes = None
        self.notification_preference = NotificationPreference.EMAIL
        self.notification_detail_level = NotificationDetailLevel.FULL
        self.subscription_status = SubscriptionStatus.ACTIVE
        self.pause_start = None
        self.pause_end = None
        self.calendar_kind: CalendarKind = CalendarKind.GOOGLE
        self.calendars: list[PersonCalendar] = []
        self.created_at = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
        self.updated_at = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
        self.roles: list[object] = []
        self.program_memberships: list[object] = []
        for k, v in overrides.items():
            setattr(self, k, v)


def test_person_response_excludes_calendar_url_when_set() -> None:
    """Bug it catches: somebody surfaces ``calendar_url`` on the
    PersonCalendarSummary or PersonResponse — the URL is a bearer
    secret that must never leave the server.
    """
    cal = PersonCalendar(
        id="cal1",
        person_id="p1",
        calendar_url="https://calendar.example.com/secret/abcd1234",
        calendar_provider="google",
        label="Personal",
        added_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
    )
    person = _StubPerson(calendars=[cal])
    resp = _person_response(person)  # type: ignore[arg-type]
    serialized = resp.model_dump_json()
    assert "abcd1234" not in serialized
    assert "secret" not in serialized
    assert len(resp.calendars) == 1
    assert resp.calendars[0].calendar_provider == "google"
    assert resp.calendars[0].label == "Personal"


def test_person_response_calendars_empty_when_none_connected() -> None:
    person = _StubPerson()
    resp = _person_response(person)  # type: ignore[arg-type]
    assert resp.calendars == []


def test_person_response_schema_does_not_declare_calendar_url() -> None:
    """Even at the schema level, the field must not exist — otherwise downstream
    code that hand-builds a PersonResponse could leak it."""
    assert "calendar_url" not in PersonResponse.model_fields
