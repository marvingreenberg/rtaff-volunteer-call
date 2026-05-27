"""Tests for the calendar service: ICS parsing and overlap logic."""

import datetime as dt
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from volunteer_call_api.services import calendar as cal_svc

FIXTURE = Path(__file__).parent / "fixtures" / "sample.ics"


def _events() -> list[cal_svc.CalendarEvent]:
    return cal_svc.parse_ics(FIXTURE.read_bytes())


def test_parse_ics_returns_three_events() -> None:
    """Bug it catches: forgetting to handle a VEVENT shape (no-DTEND, all-day)."""
    events = _events()
    assert len(events) == 3
    by_summary = {e.summary: e for e in events}
    assert "Morning meeting" in by_summary
    assert "Vacation" in by_summary
    assert "Untimed event" in by_summary


def test_parse_ics_timed_event_has_explicit_end() -> None:
    """Catches a regression where DTEND parsing flips to start+1h fallback."""
    morning = next(e for e in _events() if e.summary == "Morning meeting")
    assert morning.start == dt.datetime(2026, 6, 1, 14, 0, tzinfo=dt.timezone.utc)
    assert morning.end == dt.datetime(2026, 6, 1, 15, 0, tzinfo=dt.timezone.utc)
    assert not morning.is_all_day


def test_parse_ics_all_day_event_spans_full_day() -> None:
    """Catches mishandling of VALUE=DATE entries (treating them as midnight-only)."""
    vacation = next(e for e in _events() if e.summary == "Vacation")
    assert vacation.is_all_day
    assert vacation.start == dt.datetime(2026, 6, 15, tzinfo=dt.timezone.utc)
    assert vacation.end == dt.datetime(2026, 6, 16, tzinfo=dt.timezone.utc)


def test_parse_ics_event_without_dtend_falls_back_to_one_hour() -> None:
    """Catches a regression where missing-DTEND yields a zero-length window."""
    untimed = next(e for e in _events() if e.summary == "Untimed event")
    assert untimed.end - untimed.start == dt.timedelta(hours=1)


def test_parse_ics_in_window_expands_weekly_recurrence() -> None:
    """Bug it catches: the original parser dropped RRULE, so a weekly
    standing meeting conflicted only on its first occurrence. After
    recurring-ical-events was pulled in, every occurrence inside the
    window should appear — this test asserts four Mondays between
    2026-06-01 and 2026-06-30."""
    ics = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VEVENT
UID:weekly-standup@test
DTSTART:20260601T140000Z
DTEND:20260601T150000Z
SUMMARY:Weekly standup
RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=10
END:VEVENT
END:VCALENDAR
"""
    window_start = dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc)
    window_end = dt.datetime(2026, 6, 30, 23, 59, tzinfo=dt.timezone.utc)
    events = cal_svc.parse_ics_in_window(ics, window_start, window_end)
    # Mondays in June 2026 inside the window: Jun 1, 8, 15, 22, 29.
    assert len(events) == 5
    starts = sorted(e.start for e in events)
    assert starts[0] == dt.datetime(2026, 6, 1, 14, 0, tzinfo=dt.timezone.utc)
    assert starts[1] == dt.datetime(2026, 6, 8, 14, 0, tzinfo=dt.timezone.utc)
    assert starts[-1] == dt.datetime(2026, 6, 29, 14, 0, tzinfo=dt.timezone.utc)


def test_parse_ics_in_window_excludes_outside_window() -> None:
    """Bug it catches: a recurrence expander that ignores the window
    bounds and returns the whole RRULE series — wastes work and
    inflates the cache."""
    ics = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VEVENT
UID:daily@test
DTSTART:20260101T090000Z
DTEND:20260101T100000Z
SUMMARY:Daily
RRULE:FREQ=DAILY;COUNT=365
END:VEVENT
END:VCALENDAR
"""
    window_start = dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc)
    window_end = dt.datetime(2026, 6, 7, 23, 59, tzinfo=dt.timezone.utc)
    events = cal_svc.parse_ics_in_window(ics, window_start, window_end)
    assert len(events) == 7


@pytest.mark.parametrize(
    ("task_time_start", "task_time_end", "expected"),
    [
        # Same date, overlapping window
        (dt.time(13, 30), dt.time(14, 30), True),
        # Same date, disjoint window before event
        (dt.time(11, 0), dt.time(12, 0), False),
        # Same date, disjoint window after event
        (dt.time(15, 30), dt.time(16, 30), False),
        # Same date, contained within event
        (dt.time(14, 15), dt.time(14, 45), True),
        # Same date, no time → full day overlaps
        (None, None, True),
    ],
)
def test_overlaps_same_day_combinations(
    task_time_start: dt.time | None,
    task_time_end: dt.time | None,
    expected: bool,
) -> None:
    """Catches off-by-one in interval comparison (< vs <=)."""
    morning = next(e for e in _events() if e.summary == "Morning meeting")
    assert (
        cal_svc.overlaps(morning, dt.date(2026, 6, 1), task_time_start, task_time_end) is expected
    )


def test_overlaps_different_day_never_conflicts() -> None:
    morning = next(e for e in _events() if e.summary == "Morning meeting")
    assert cal_svc.overlaps(morning, dt.date(2026, 6, 2), None, None) is False


def test_overlaps_task_with_no_date_never_conflicts() -> None:
    """A task with no date can't conflict — would otherwise crash on combine()."""
    morning = next(e for e in _events() if e.summary == "Morning meeting")
    assert cal_svc.overlaps(morning, None, None, None) is False


@pytest.mark.asyncio
async def test_fetch_and_parse_returns_empty_on_http_error() -> None:
    """Network failures are non-fatal; a returned empty list keeps the page rendering."""
    with patch.object(cal_svc.httpx, "AsyncClient") as mock_client:
        instance = AsyncMock()
        instance.get.side_effect = httpx.ConnectError("boom")
        mock_client.return_value.__aenter__.return_value = instance
        result = await cal_svc.fetch_and_parse("https://example.invalid/calendar.ics")
    assert result == []


@pytest.mark.asyncio
async def test_fetch_and_parse_returns_empty_on_bad_payload() -> None:
    """A 200 with un-parseable body shouldn't throw out to the route either."""
    with patch.object(cal_svc.httpx, "AsyncClient") as mock_client:
        response = AsyncMock()
        response.raise_for_status = lambda: None
        response.content = b"not actually an ics file"
        instance = AsyncMock()
        instance.get.return_value = response
        mock_client.return_value.__aenter__.return_value = instance
        result = await cal_svc.fetch_and_parse("https://example.invalid/calendar.ics")
    assert result == []


@pytest.mark.asyncio
async def test_get_events_for_person_caches_results() -> None:
    """Second call within TTL must not re-fetch — that's the whole point of the cache."""
    cal_svc._cache.clear()
    fetch_calls = 0

    async def fake_fetch(
        _url: str,
        _window: tuple[object, object] | None = None,
    ) -> list[cal_svc.CalendarEvent]:
        nonlocal fetch_calls
        fetch_calls += 1
        return _events()

    with patch.object(cal_svc, "fetch_and_parse", side_effect=fake_fetch):
        events1 = await cal_svc.get_events_for_person("p1", "https://x/cal.ics")
        events2 = await cal_svc.get_events_for_person("p1", "https://x/cal.ics")
    assert fetch_calls == 1
    assert events1 == events2


@pytest.mark.asyncio
async def test_validate_calendar_url_raises_friendly_message_on_unreachable() -> None:
    """Connect-time validation must surface 'couldn't reach this URL' rather
    than silently storing a bad URL — that's the exact bug we're fixing.
    Without this guard, a typo lets a volunteer 'connect' a URL that will
    never produce a single conflict warning."""
    with patch.object(cal_svc.httpx, "AsyncClient") as mock_client:
        instance = AsyncMock()
        instance.get.side_effect = httpx.ConnectError("boom")
        mock_client.return_value.__aenter__.return_value = instance
        with pytest.raises(cal_svc.CalendarValidationError) as exc:
            await cal_svc.validate_calendar_url("https://example.invalid/calendar.ics")
    assert "Couldn't reach" in str(exc.value)


@pytest.mark.asyncio
async def test_validate_calendar_url_raises_on_4xx_status() -> None:
    """Most common real-world failure: user pastes a stale share link that's
    been revoked, host responds with 401/403/404. Surface the status so the
    user can troubleshoot rather than wondering why nothing flags."""
    with patch.object(cal_svc.httpx, "AsyncClient") as mock_client:
        response = AsyncMock()
        response.status_code = 404
        response.content = b""
        instance = AsyncMock()
        instance.get.return_value = response
        mock_client.return_value.__aenter__.return_value = instance
        with pytest.raises(cal_svc.CalendarValidationError) as exc:
            await cal_svc.validate_calendar_url("https://example.invalid/calendar.ics")
    assert "404" in str(exc.value)


@pytest.mark.asyncio
async def test_validate_calendar_url_raises_on_non_ical_body() -> None:
    """User pastes the human-facing share *page* URL instead of the ICS
    subscribe URL — server returns 200 + HTML. Without this branch the
    connect succeeds but no events are ever found."""
    with patch.object(cal_svc.httpx, "AsyncClient") as mock_client:
        response = AsyncMock()
        response.status_code = 200
        response.content = b"<html><body>not iCal</body></html>"
        instance = AsyncMock()
        instance.get.return_value = response
        mock_client.return_value.__aenter__.return_value = instance
        with pytest.raises(cal_svc.CalendarValidationError) as exc:
            await cal_svc.validate_calendar_url("https://example.invalid/calendar.ics")
    assert "valid iCal" in str(exc.value)


@pytest.mark.asyncio
async def test_validate_calendar_url_succeeds_on_valid_ics() -> None:
    """Pin the happy path: a real iCal payload returns None (no exception)."""
    with patch.object(cal_svc.httpx, "AsyncClient") as mock_client:
        response = AsyncMock()
        response.status_code = 200
        response.content = FIXTURE.read_bytes()
        instance = AsyncMock()
        instance.get.return_value = response
        mock_client.return_value.__aenter__.return_value = instance
        # No exception means success.
        await cal_svc.validate_calendar_url("https://example.invalid/calendar.ics")


@pytest.mark.asyncio
async def test_fetch_and_parse_still_lenient_after_validation_added() -> None:
    """Regression guard: validation lives in a separate function — the
    read path (fetch_and_parse) must keep swallowing errors, otherwise
    a transient calendar host outage would break the volunteering page
    for every connected user."""
    with patch.object(cal_svc.httpx, "AsyncClient") as mock_client:
        instance = AsyncMock()
        instance.get.side_effect = httpx.ConnectError("boom")
        mock_client.return_value.__aenter__.return_value = instance
        result = await cal_svc.fetch_and_parse("https://example.invalid/calendar.ics")
    assert result == []  # MUST NOT raise


@pytest.mark.asyncio
async def test_invalidate_person_cache_forces_refetch() -> None:
    """Disconnect/reconnect must drop the cached events."""
    cal_svc._cache.clear()
    fetch_calls = 0

    async def fake_fetch(
        _url: str,
        _window: tuple[object, object] | None = None,
    ) -> list[cal_svc.CalendarEvent]:
        nonlocal fetch_calls
        fetch_calls += 1
        return []

    with patch.object(cal_svc, "fetch_and_parse", side_effect=fake_fetch):
        await cal_svc.get_events_for_person("p1", "https://x/cal.ics")
        cal_svc.invalidate_person_cache("p1")
        await cal_svc.get_events_for_person("p1", "https://x/cal.ics")
    assert fetch_calls == 2
