"""Calendar conflict detection via user-pasted iCal URLs.

Fetches the user's private iCal URL on demand, caches parsed events
per-user with a short TTL, and computes overlap with task windows.
No OAuth, no scheduler — works entirely off the URL the user pastes
into their profile.

Errors (network, parse, 4xx) are intentionally non-fatal: the user
sees "no conflicts" and the page renders. A failed fetch logs a
warning but never raises out to the route.
"""

from __future__ import annotations

import datetime as dt
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx
import recurring_ical_events
from icalendar import Calendar
from icalendar.prop import vDatetime

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 5 * 60
FETCH_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class CalendarEvent:
    """A normalized busy-window from the user's calendar."""

    start: dt.datetime
    end: dt.datetime
    summary: str | None
    is_all_day: bool


# Process-local cache: keyed by (person_id, calendar_url). Cloud Run with
# multiple instances will fetch per-instance; acceptable for this volume.
_cache: dict[
    tuple[str, str, dt.datetime | None, dt.datetime | None],
    tuple[float, list[CalendarEvent]],
] = {}


def _to_utc_datetime(value: dt.datetime | dt.date) -> tuple[dt.datetime, bool]:
    """Normalize a vDatetime/vDate value to a tz-aware UTC datetime.

    Returns (datetime, is_all_day). All-day events are anchored at 00:00 UTC
    on the given date and run for 24 hours unless paired with an explicit
    DTEND.
    """
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt.timezone.utc)
        return value.astimezone(dt.timezone.utc), False
    # plain date → all-day
    return dt.datetime.combine(value, dt.time(0, 0), tzinfo=dt.timezone.utc), True


def _vevent_to_event(component: Any) -> CalendarEvent | None:
    """Translate a single VEVENT (raw or recurrence-expanded) into a
    normalized CalendarEvent. Returns None if DTSTART is missing.

    Typed ``Any`` because icalendar's Component shape is loosely typed
    and recurring-ical-events yields the same component-like objects.
    """
    dtstart_raw = component.get("DTSTART")
    if dtstart_raw is None:
        return None
    start, all_day = _to_utc_datetime(dtstart_raw.dt)

    dtend_raw = component.get("DTEND")
    if dtend_raw is not None:
        end, _ = _to_utc_datetime(dtend_raw.dt)
    elif all_day:
        end = start + dt.timedelta(days=1)
    else:
        duration = component.get("DURATION")
        end = start + (duration.dt if duration is not None else dt.timedelta(hours=1))

    summary_raw = component.get("SUMMARY")
    summary = str(summary_raw) if summary_raw is not None else None
    return CalendarEvent(start=start, end=end, summary=summary, is_all_day=all_day)


def parse_ics(payload: bytes | str) -> list[CalendarEvent]:
    """Parse an ICS payload, one event per VEVENT (no RRULE expansion).

    Kept for the calendar-validation path, which only needs to confirm
    the feed parses. Conflict detection uses
    :func:`parse_ics_in_window`, which expands recurrences.
    """
    cal = Calendar.from_ical(payload)
    events: list[CalendarEvent] = []
    for component in cal.walk("VEVENT"):
        ev = _vevent_to_event(component)
        if ev is not None:
            events.append(ev)
    return events


def parse_ics_in_window(
    payload: bytes | str,
    window_start: dt.datetime,
    window_end: dt.datetime,
) -> list[CalendarEvent]:
    """Parse an ICS payload and expand RRULE-bearing events in the window.

    Without this expansion a weekly standing meeting only conflicts on
    its first occurrence — the original bug recurring-ical-events was
    pulled in to fix. The library returns regular VEVENT components for
    each occurrence; we translate them through the same normalizer used
    by :func:`parse_ics`.
    """
    cal = Calendar.from_ical(payload)
    events: list[CalendarEvent] = []
    # recurring-ical-events returns vEvent components covering both
    # one-shot and expanded recurrence instances within the window.
    for component in recurring_ical_events.of(cal).between(window_start, window_end):
        ev = _vevent_to_event(component)
        if ev is not None:
            events.append(ev)
    return events


async def fetch_payload(url: str) -> bytes | None:
    """Fetch the iCal URL. Returns ``None`` on any error."""
    try:
        async with httpx.AsyncClient(
            timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=True
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
    except httpx.HTTPError as exc:
        logger.warning("Calendar fetch failed for URL ending …%s: %s", url[-8:], exc)
        return None


async def fetch_and_parse(
    url: str,
    window: tuple[dt.datetime, dt.datetime] | None = None,
) -> list[CalendarEvent]:
    """Fetch the iCal URL and parse it. Returns [] on any error.

    When ``window`` is provided, RRULEs are expanded so recurring
    events conflict on every occurrence inside the window. Without a
    window (callers that only want one-shot events for inspection),
    behaves like the old DTSTART-only parser.
    """
    payload = await fetch_payload(url)
    if payload is None:
        return []
    try:
        if window is None:
            return parse_ics(payload)
        return parse_ics_in_window(payload, *window)
    except (ValueError, KeyError, AttributeError, TypeError) as exc:
        logger.warning("Calendar parse failed for URL ending …%s: %s", url[-8:], exc)
        return []


class CalendarValidationError(Exception):
    """Raised by validate_calendar_url with a user-facing message.

    Distinct from fetch_and_parse's swallow-and-return-[] behavior: the
    conflict-rendering path stays lenient on transient errors, but at
    connect time we want to surface the failure so the user knows their
    URL is bad and won't silently get no warnings forever.
    """


async def validate_calendar_url(url: str) -> None:
    """Fetch the URL and confirm it returns parseable iCal.

    Raises CalendarValidationError(message) where `message` is suitable to
    show to the end user. Returns None on success.
    """
    try:
        async with httpx.AsyncClient(
            timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=True
        ) as client:
            resp = await client.get(url)
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError):
        raise CalendarValidationError("Couldn't reach this URL. Check it and try again.")

    if resp.status_code >= 400:
        raise CalendarValidationError(
            f"The calendar host returned {resp.status_code}. "
            "The URL may be wrong or no longer shared publicly."
        )

    try:
        parse_ics(resp.content)
    except (ValueError, KeyError, AttributeError, TypeError):
        raise CalendarValidationError("That URL didn't return a valid iCal feed.")


async def get_events_for_person(
    person_id: str,
    calendar_url: str,
    window: tuple[dt.datetime, dt.datetime] | None = None,
) -> list[CalendarEvent]:
    """Cached wrapper. Fetches on cache miss / expiry.

    The cache is keyed by (person_id, url, window) so concurrent
    callers asking for different windows don't poison each other's
    expansion. Callers that don't need recurrences (e.g. the
    validate-on-connect path) can pass ``window=None`` and reuse the
    cheaper DTSTART-only path.
    """
    key: tuple[str, str, dt.datetime | None, dt.datetime | None] = (
        person_id,
        calendar_url,
        window[0] if window else None,
        window[1] if window else None,
    )
    now = time.monotonic()
    cached = _cache.get(key)
    if cached is not None and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]
    events = await fetch_and_parse(calendar_url, window)
    _cache[key] = (now, events)
    return events


def invalidate_person_cache(person_id: str) -> None:
    """Drop all cache entries for a person (e.g., on disconnect)."""
    keys = [k for k in list(_cache) if k[0] == person_id]
    for k in keys:
        del _cache[k]


def _task_window(
    task_date: dt.date, time_start: dt.time | None, time_end: dt.time | None
) -> tuple[dt.datetime, dt.datetime]:
    """Build a UTC datetime range for a task. Treats naive task times as UTC.

    If the task has no time, the window is the full UTC day. Cross-timezone
    accuracy is a v2 concern — for the volunteer-call use case the dates
    matter much more than the hours.
    """
    start_t = time_start or dt.time(0, 0)
    if time_end is not None:
        end_dt = dt.datetime.combine(task_date, time_end, tzinfo=dt.timezone.utc)
    else:
        end_dt = dt.datetime.combine(task_date, dt.time(23, 59, 59), tzinfo=dt.timezone.utc)
    start_dt = dt.datetime.combine(task_date, start_t, tzinfo=dt.timezone.utc)
    return start_dt, end_dt


def overlaps(
    event: CalendarEvent,
    task_date: dt.date | None,
    time_start: dt.time | None,
    time_end: dt.time | None,
) -> bool:
    """Does the event overlap the task window? Tasks with no date never conflict."""
    if task_date is None:
        return False
    task_start, task_end = _task_window(task_date, time_start, time_end)
    return event.start < task_end and event.end > task_start


# Re-export for tests that want to construct vDatetime values directly.
__all__ = [
    "CalendarEvent",
    "CalendarValidationError",
    "parse_ics",
    "parse_ics_in_window",
    "fetch_and_parse",
    "validate_calendar_url",
    "get_events_for_person",
    "invalidate_person_cache",
    "overlaps",
    "vDatetime",
]
