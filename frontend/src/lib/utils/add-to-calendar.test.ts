import { describe, it, expect } from "vitest";
import {
  buildIcs,
  chooseCalendarAction,
  googleCalendarUrl,
  outlookCalendarUrl,
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

describe("outlookCalendarUrl", () => {
  it("uses outlook.office.com with /deeplink/compose path", () => {
    // Bug it catches: pointing at outlook.live.com only — that breaks
    // for users on 365 work accounts (the most common case here).
    const url = outlookCalendarUrl(base);
    expect(url).toContain(
      "https://outlook.office.com/calendar/0/deeplink/compose",
    );
    expect(url).toContain("rru=addevent");
    expect(url).toContain("subject=RT-AFF+Volunteer+-+Roof+patch");
  });

  it("emits ISO-8601 local timestamps without Z", () => {
    // Bug it catches: shoving a Z onto the time, which makes Outlook
    // shift the event to the user's local TZ from UTC and end up
    // hours off.
    const url = outlookCalendarUrl(base);
    expect(url).toContain("startdt=2026-07-04T09%3A00%3A00");
    expect(url).toContain("enddt=2026-07-04T12%3A30%3A00");
    expect(url).not.toContain("Z");
  });
});

describe("chooseCalendarAction", () => {
  it("returns a link action for google", () => {
    // Bug it catches: a future refactor that swaps kinds returns the
    // wrong URL builder for Google users.
    const action = chooseCalendarAction(base, "google");
    expect(action.kind).toBe("link");
    if (action.kind === "link")
      expect(action.href).toContain("calendar.google.com");
  });

  it("returns a link action for outlook", () => {
    const action = chooseCalendarAction(base, "outlook");
    expect(action.kind).toBe("link");
    if (action.kind === "link")
      expect(action.href).toContain("outlook.office.com");
  });

  it("returns download + hint for apple", () => {
    // Bug it catches: silently producing a non-working webcal:// URL
    // for Apple — there's no good deeplink, the only correct path is
    // .ics with an instruction.
    const action = chooseCalendarAction(base, "apple");
    expect(action.kind).toBe("download");
    if (action.kind === "download") {
      expect(action.hint).toMatch(/apple/i);
    }
  });

  it("returns download with no hint for other", () => {
    const action = chooseCalendarAction(base, "other");
    expect(action.kind).toBe("download");
    if (action.kind === "download") {
      expect(action.hint).toBeNull();
    }
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
