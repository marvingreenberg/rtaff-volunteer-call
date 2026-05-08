"""Schema invariants. The big one: calendar_url must never escape via PersonResponse."""

import datetime as dt

from volunteer_call_api.models.person import (
    NotificationDetailLevel,
    NotificationPreference,
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
        self.access_token = None
        self.notification_preference = NotificationPreference.EMAIL
        self.notification_detail_level = NotificationDetailLevel.FULL
        self.subscription_status = SubscriptionStatus.ACTIVE
        self.pause_start = None
        self.pause_end = None
        self.calendar_url: str | None = None
        self.calendar_provider: str | None = None
        self.calendar_url_added_at: dt.datetime | None = None
        self.created_at = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
        self.updated_at = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
        self.roles: list[object] = []
        self.program_memberships: list[object] = []
        for k, v in overrides.items():
            setattr(self, k, v)


def test_person_response_excludes_calendar_url_when_set() -> None:
    """Bug it catches: somebody adds `calendar_url=person.calendar_url` to _person_response."""
    person = _StubPerson(
        calendar_url="https://calendar.example.com/secret/abcd1234",
        calendar_provider="google",
    )
    resp = _person_response(person)  # type: ignore[arg-type]
    serialized = resp.model_dump_json()
    assert "abcd1234" not in serialized
    assert "secret" not in serialized
    assert resp.calendar_connected is True
    assert resp.calendar_provider == "google"


def test_person_response_calendar_connected_false_when_url_absent() -> None:
    person = _StubPerson()
    resp = _person_response(person)  # type: ignore[arg-type]
    assert resp.calendar_connected is False
    assert resp.calendar_provider is None


def test_person_response_schema_does_not_declare_calendar_url() -> None:
    """Even at the schema level, the field must not exist — otherwise downstream
    code that hand-builds a PersonResponse could leak it."""
    assert "calendar_url" not in PersonResponse.model_fields
