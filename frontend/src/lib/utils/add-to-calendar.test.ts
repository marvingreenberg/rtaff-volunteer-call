import { describe, it, expect } from "vitest";
import {
  buildIcs,
  googleCalendarUrl,
  type CalendarEvent,
} from "./add-to-calendar";

const base: CalendarEvent = {
  date: "2026-07-04",
  time_start: "09:00",
  time_end: "12:30",
  title: "RT-AFF Volunteer - Roof patch",
  location: "102 Maple Ave",
  description: "Volunteer call: Spring NRD",
};

describe("googleCalendarUrl", () => {
  it("encodes the basic event params", () => {
    // Bug it catches: a refactor swaps to `&` string concatenation
    // without URLSearchParams and the title's space breaks the link.
    const url = googleCalendarUrl(base);
    expect(url).toContain("https://calendar.google.com/calendar/render");
    expect(url).toContain("action=TEMPLATE");
    expect(url).toContain("text=RT-AFF+Volunteer+-+Roof+patch");
    expect(url).toContain("dates=20260704T090000%2F20260704T123000");
    expect(url).toContain("location=102+Maple+Ave");
  });

  it("omits location/details when missing", () => {
    // Bug it catches: a null location is serialized as "null" string.
    const url = googleCalendarUrl({
      ...base,
      location: null,
      description: null,
    });
    expect(url).not.toContain("location=");
    expect(url).not.toContain("details=");
    expect(url).not.toContain("null");
  });

  it("falls back to default times when time_start/time_end are null", () => {
    // Bug it catches: nulls flow through and produce
    // "dates=20260704T/20260704T" which Google rejects.
    const url = googleCalendarUrl({
      ...base,
      time_start: null,
      time_end: null,
    });
    expect(url).toContain("dates=20260704T090000%2F20260704T123000");
  });
});

describe("buildIcs", () => {
  it("uses CRLF line endings (RFC 5545)", () => {
    // Bug it catches: a join("\n") regression — Outlook/Mail.app silently
    // accept this but stricter clients (some Android calendars) drop the
    // event entirely.
    const ics = buildIcs(base);
    expect(ics).toContain("\r\n");
    expect(ics.split("\r\n")[0]).toBe("BEGIN:VCALENDAR");
  });

  it("omits LOCATION when none provided", () => {
    const ics = buildIcs({ ...base, location: null });
    expect(ics).not.toMatch(/LOCATION:/);
  });
});
