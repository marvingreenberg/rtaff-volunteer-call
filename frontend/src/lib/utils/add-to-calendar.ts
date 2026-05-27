/**
 * Add-to-calendar helpers.
 *
 * Google Calendar's "render event" URL is the primary path — one click
 * pops a pre-filled event in the user's primary calendar. The `.ics`
 * download is the fallback for users who use Apple Calendar / Outlook
 * desktop / anything else.
 *
 * Times are emitted in floating (no-Z, no offset) form — both Google
 * and the iCal spec accept this and interpret it as the viewer's local
 * time, which is what we want for a regional NoVA volunteer use case.
 * Cross-TZ correctness is a separate todo.
 */

export interface CalendarEvent {
  /** ISO date (YYYY-MM-DD). */
  date: string;
  /** Start time as HH:MM or HH:MM:SS, or null for an all-day event. */
  time_start: string | null;
  /** End time, same format. Falls back to a default window if absent. */
  time_end: string | null;
  /** Short title shown in the calendar entry. */
  title: string;
  /** Full address; used for both maps and event location. Optional. */
  location?: string | null;
  /** Free-form description; e.g. "Volunteer call: Spring NRD". */
  description?: string | null;
}

// Default-day fallbacks when the assignment has no start/end time set.
// 9:00 — 12:30 matches the previous ICS fallback in volunteering page.
const DEFAULT_START = "09:00:00";
const DEFAULT_END = "12:30:00";

function padTime(t: string | null, fallback: string): string {
  const v = t || fallback;
  // Accept HH:MM or HH:MM:SS — pad to HHMMSS.
  const compact = v.replace(/:/g, "");
  return compact.length === 4 ? compact + "00" : compact;
}

function compactDate(isoDate: string): string {
  return isoDate.replace(/-/g, "");
}

/** Google Calendar's TEMPLATE URL for a single event. */
export function googleCalendarUrl(event: CalendarEvent): string {
  const d = compactDate(event.date);
  const start = padTime(event.time_start, DEFAULT_START);
  const end = padTime(event.time_end, DEFAULT_END);
  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: event.title,
    dates: `${d}T${start}/${d}T${end}`,
  });
  if (event.location) params.set("location", event.location);
  if (event.description) params.set("details", event.description);
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

/** RFC 5545 .ics body for the same event. */
export function buildIcs(event: CalendarEvent): string {
  const d = compactDate(event.date);
  const start = padTime(event.time_start, DEFAULT_START);
  const end = padTime(event.time_end, DEFAULT_END);
  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//RT-AFF//Volunteer//EN",
    "BEGIN:VEVENT",
    `DTSTART:${d}T${start}`,
    `DTEND:${d}T${end}`,
    `SUMMARY:${event.title}`,
    event.location ? `LOCATION:${event.location}` : "",
    event.description ? `DESCRIPTION:${event.description}` : "",
    "END:VEVENT",
    "END:VCALENDAR",
  ].filter(Boolean);
  return lines.join("\r\n");
}

/** Trigger a browser download of an .ics file for the event. */
export function downloadIcs(event: CalendarEvent): void {
  const blob = new Blob([buildIcs(event)], { type: "text/calendar" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `rt-aff-${event.date}.ics`;
  link.click();
  URL.revokeObjectURL(url);
}
