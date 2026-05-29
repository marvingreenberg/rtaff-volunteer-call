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

/** Mirrors backend CalendarKind. Drives the deeplink/download choice. */
export type CalendarKind = "google" | "apple" | "outlook" | "other";

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

/**
 * Outlook (Live + 365) deeplink for a single event.
 *
 * Uses the office.com host because it works for both consumer and
 * commercial accounts in modern browsers — the user gets routed to
 * outlook.live.com automatically if they're signed into a personal
 * account. `path=/calendar/action/compose&rru=addevent` opens the
 * event-compose pane with the fields pre-filled.
 *
 * Timestamps are ISO-8601 *without* a Z, so Outlook interprets them in
 * the viewer's local timezone — same convention as the Google deeplink.
 */
export function outlookCalendarUrl(event: CalendarEvent): string {
  const startTime = (event.time_start || DEFAULT_START).replace(
    /:(\d\d)$/,
    ":$1",
  );
  const endTime = (event.time_end || DEFAULT_END).replace(/:(\d\d)$/, ":$1");
  const startdt = `${event.date}T${pad8601(startTime)}`;
  const enddt = `${event.date}T${pad8601(endTime)}`;
  const params = new URLSearchParams({
    path: "/calendar/action/compose",
    rru: "addevent",
    subject: event.title,
    startdt,
    enddt,
  });
  if (event.location) params.set("location", event.location);
  if (event.description) params.set("body", event.description);
  return `https://outlook.office.com/calendar/0/deeplink/compose?${params.toString()}`;
}

function pad8601(t: string): string {
  // Accept HH:MM and HH:MM:SS; emit HH:MM:SS for Outlook's ISO-8601 parser.
  const parts = t.split(":");
  if (parts.length === 2) return `${t}:00`;
  return t;
}

/**
 * Action shape returned by ``chooseCalendarAction`` — either a URL to
 * open in a new tab (google, outlook) or a sentinel telling the caller
 * to trigger the .ics download path (apple, other). For Apple, ``hint``
 * carries a short string the UI surfaces so the user knows what to do
 * with the downloaded file.
 */
export type CalendarAction =
  | { kind: "link"; href: string; label: string }
  | { kind: "download"; label: string; hint: string | null };

/**
 * Pick the right "Add to calendar" action for the user's preferred app.
 * Apple has no useful deeplink — the caller should call ``downloadIcs``
 * and surface ``hint`` so the user knows to double-click the file.
 */
export function chooseCalendarAction(
  _event: CalendarEvent,
  kind: CalendarKind,
): CalendarAction {
  if (kind === "google") {
    return {
      kind: "link",
      href: googleCalendarUrl(_event),
      label: "Add to Google Calendar",
    };
  }
  if (kind === "outlook") {
    return {
      kind: "link",
      href: outlookCalendarUrl(_event),
      label: "Add to Outlook",
    };
  }
  if (kind === "apple") {
    return {
      kind: "download",
      label: "Download for Apple Calendar",
      hint: "Open the downloaded file to add the event to Apple Calendar.",
    };
  }
  return {
    kind: "download",
    label: "Download .ics",
    hint: null,
  };
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
