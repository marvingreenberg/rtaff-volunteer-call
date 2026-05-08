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

    async def fake_fetch(_url: str) -> list[cal_svc.CalendarEvent]:
        nonlocal fetch_calls
        fetch_calls += 1
        return _events()

    with patch.object(cal_svc, "fetch_and_parse", side_effect=fake_fetch):
        events1 = await cal_svc.get_events_for_person("p1", "https://x/cal.ics")
        events2 = await cal_svc.get_events_for_person("p1", "https://x/cal.ics")
    assert fetch_calls == 1
    assert events1 == events2


@pytest.mark.asyncio
async def test_invalidate_person_cache_forces_refetch() -> None:
    """Disconnect/reconnect must drop the cached events."""
    cal_svc._cache.clear()
    fetch_calls = 0

    async def fake_fetch(_url: str) -> list[cal_svc.CalendarEvent]:
        nonlocal fetch_calls
        fetch_calls += 1
        return []

    with patch.object(cal_svc, "fetch_and_parse", side_effect=fake_fetch):
        await cal_svc.get_events_for_person("p1", "https://x/cal.ics")
        cal_svc.invalidate_person_cache("p1")
        await cal_svc.get_events_for_person("p1", "https://x/cal.ics")
    assert fetch_calls == 2
