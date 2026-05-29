import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import CalendarConnectPanel from "./CalendarConnectPanel.svelte";
import type { PersonCalendarSummary } from "$lib/api/types";

vi.mock("$lib/api/client", () => ({
  people: {
    addCalendar: vi.fn(),
    removeCalendar: vi.fn(),
  },
}));

vi.mock("$lib/stores/confirm.svelte", () => ({
  confirmDialog: vi.fn(),
}));

import { people } from "$lib/api/client";
import { confirmDialog } from "$lib/stores/confirm.svelte";

const addCal = people.addCalendar as ReturnType<typeof vi.fn>;
const removeCal = people.removeCalendar as ReturnType<typeof vi.fn>;
const confirmMock = confirmDialog as ReturnType<typeof vi.fn>;

beforeEach(() => {
  addCal.mockReset();
  removeCal.mockReset();
});

function cal(
  overrides: Partial<PersonCalendarSummary> = {},
): PersonCalendarSummary {
  return {
    id: "cal-1",
    calendar_provider: "Google",
    label: "Personal",
    added_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("CalendarConnectPanel", () => {
  it("lists each connected calendar with its label + provider", () => {
    // Bug it catches: a refactor renders only the first calendar in the
    // list, defeating the multi-calendar UX.
    render(CalendarConnectPanel, {
      props: {
        personId: "p1",
        calendars: [
          cal({ id: "a", label: "Personal", calendar_provider: "Google" }),
          cal({ id: "b", label: "Work", calendar_provider: "Outlook" }),
        ],
        onChanged: vi.fn(),
      },
    });
    expect(screen.getByText("Personal")).toBeInTheDocument();
    expect(screen.getByText("Work")).toBeInTheDocument();
    expect(screen.getByText("Google")).toBeInTheDocument();
    expect(screen.getByText("Outlook")).toBeInTheDocument();
  });

  it("renders an empty-state hint when no calendars are connected", () => {
    render(CalendarConnectPanel, {
      props: { personId: "p1", calendars: [], onChanged: vi.fn() },
    });
    expect(screen.getByText(/no calendars connected/i)).toBeInTheDocument();
  });

  it("submitting the Add form calls addCalendar with URL + label + provider", async () => {
    addCal.mockResolvedValue({});
    const onChanged = vi.fn();
    render(CalendarConnectPanel, {
      props: { personId: "person-123", calendars: [], onChanged },
    });

    await fireEvent.click(
      screen.getByRole("button", { name: /add a calendar/i }),
    );

    const labelInput = screen.getByPlaceholderText(/personal, work/i);
    const urlInput = screen.getByPlaceholderText(/https:\/\//);
    const providerInput = screen.getByPlaceholderText(
      /google, apple, outlook/i,
    );
    await fireEvent.input(labelInput, { target: { value: "Work" } });
    await fireEvent.input(urlInput, { target: { value: "https://x/cal.ics" } });
    await fireEvent.input(providerInput, { target: { value: "Outlook" } });

    await fireEvent.click(screen.getByRole("button", { name: /^connect$/i }));

    expect(addCal).toHaveBeenCalledWith("person-123", {
      calendar_url: "https://x/cal.ics",
      calendar_provider: "Outlook",
      label: "Work",
    });
    expect(onChanged).toHaveBeenCalled();
  });

  it("displays the server error and keeps the form open on add failure", async () => {
    addCal.mockRejectedValue(
      new Error("That URL didn't return a valid iCal feed."),
    );
    const onChanged = vi.fn();
    render(CalendarConnectPanel, {
      props: { personId: "p1", calendars: [], onChanged },
    });

    await fireEvent.click(
      screen.getByRole("button", { name: /add a calendar/i }),
    );
    const urlInput = screen.getByPlaceholderText(/https:\/\//);
    await fireEvent.input(urlInput, { target: { value: "https://bad/url" } });
    await fireEvent.click(screen.getByRole("button", { name: /^connect$/i }));

    expect(
      await screen.findByText(/didn't return a valid iCal feed/i),
    ).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/https:\/\//)).toBeInTheDocument();
    expect(onChanged).not.toHaveBeenCalled();
  });

  it("× button calls removeCalendar(personId, calId) after confirm", async () => {
    removeCal.mockResolvedValue(undefined);
    confirmMock.mockResolvedValue(true);
    const onChanged = vi.fn();
    render(CalendarConnectPanel, {
      props: {
        personId: "p1",
        calendars: [cal({ id: "cal-x", label: "Personal" })],
        onChanged,
      },
    });
    await fireEvent.click(
      screen.getByRole("button", { name: /disconnect personal/i }),
    );
    // confirmDialog is awaited inside the handler; flush microtasks so
    // the subsequent removeCalendar call resolves before assertions.
    await Promise.resolve();
    await Promise.resolve();
    expect(confirmMock).toHaveBeenCalled();
    expect(removeCal).toHaveBeenCalledWith("p1", "cal-x");
    expect(onChanged).toHaveBeenCalled();
  });

  it("Help section defaults to General info; clicking provider tabs swaps content", async () => {
    render(CalendarConnectPanel, {
      props: { personId: "p1", calendars: [], onChanged: vi.fn() },
    });
    await fireEvent.click(
      screen.getByRole("button", { name: /add a calendar/i }),
    );

    const generalTab = screen.getByRole("tab", { name: /general info/i });
    expect(generalTab.getAttribute("aria-selected")).toBe("true");
    expect(screen.getByText(/private subscription link/i)).toBeInTheDocument();

    const googleTab = screen.getByRole("tab", { name: /google/i });
    await fireEvent.click(googleTab);
    expect(googleTab.getAttribute("aria-selected")).toBe("true");
    expect(generalTab.getAttribute("aria-selected")).toBe("false");
    expect(
      screen.getByText(/access permissions for events/i),
    ).toBeInTheDocument();
  });
});
