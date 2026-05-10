import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import CalendarConnectPanel from "./CalendarConnectPanel.svelte";

vi.mock("$lib/api/client", () => ({
  people: {
    connectCalendar: vi.fn(),
    disconnectCalendar: vi.fn(),
  },
}));

import { people } from "$lib/api/client";

const connect = people.connectCalendar as ReturnType<typeof vi.fn>;
const disconnect = people.disconnectCalendar as ReturnType<typeof vi.fn>;

beforeEach(() => {
  connect.mockReset();
  disconnect.mockReset();
});

describe("CalendarConnectPanel", () => {
  it("button uses the requested tooltip text", () => {
    // The literal tooltip copy is part of the spec — pinning it catches
    // a silent edit that strips the explanatory hover.
    render(CalendarConnectPanel, {
      props: {
        personId: "p1",
        calendarConnected: false,
        calendarProvider: null,
        onChanged: vi.fn(),
      },
    });
    const button = screen.getByRole("button", { name: /connect calendar/i });
    expect(button.getAttribute("title")).toBe(
      "Connect your calendar to make volunteering simpler",
    );
  });

  it("shows connected status + Disconnect when calendarConnected=true", () => {
    render(CalendarConnectPanel, {
      props: {
        personId: "p1",
        calendarConnected: true,
        calendarProvider: "Google",
        onChanged: vi.fn(),
      },
    });
    expect(
      screen.getByRole("button", { name: /calendar connected · google/i }),
    ).toBeInTheDocument();
  });

  it("submitting the form calls connectCalendar with the typed URL+provider", async () => {
    connect.mockResolvedValue({});
    const onChanged = vi.fn();
    render(CalendarConnectPanel, {
      props: {
        personId: "person-123",
        calendarConnected: false,
        calendarProvider: null,
        onChanged,
      },
    });

    await fireEvent.click(
      screen.getByRole("button", { name: /connect calendar/i }),
    );

    const urlInput = screen.getByPlaceholderText(/https:\/\//);
    const providerInput = screen.getByPlaceholderText(
      /google, apple, outlook/i,
    );
    await fireEvent.input(urlInput, { target: { value: "https://x/cal.ics" } });
    await fireEvent.input(providerInput, { target: { value: "Google" } });

    const submit = screen.getByRole("button", { name: /^connect$/i });
    await fireEvent.click(submit);

    expect(connect).toHaveBeenCalledWith("person-123", {
      calendar_url: "https://x/cal.ics",
      calendar_provider: "Google",
    });
    expect(onChanged).toHaveBeenCalled();
  });

  it("displays the server error and does NOT collapse the panel on connect failure", async () => {
    // Pinning that 422 messages stay visible — closing the panel on error
    // would be the worst possible UX since the user would have to re-open
    // and re-paste their URL to even see what went wrong.
    connect.mockRejectedValue(
      new Error("That URL didn't return a valid iCal feed."),
    );
    const onChanged = vi.fn();
    render(CalendarConnectPanel, {
      props: {
        personId: "p1",
        calendarConnected: false,
        calendarProvider: null,
        onChanged,
      },
    });

    await fireEvent.click(
      screen.getByRole("button", { name: /connect calendar/i }),
    );
    const urlInput = screen.getByPlaceholderText(/https:\/\//);
    await fireEvent.input(urlInput, { target: { value: "https://bad/url" } });
    await fireEvent.click(screen.getByRole("button", { name: /^connect$/i }));

    expect(
      await screen.findByText(/didn't return a valid iCal feed/i),
    ).toBeInTheDocument();
    // Form is still visible (panel didn't collapse).
    expect(screen.getByPlaceholderText(/https:\/\//)).toBeInTheDocument();
    expect(onChanged).not.toHaveBeenCalled();
  });

  it("disconnect button calls disconnectCalendar after confirm", async () => {
    disconnect.mockResolvedValue({});
    const confirmSpy = vi
      .spyOn(window, "confirm")
      .mockImplementation(() => true);
    const onChanged = vi.fn();
    render(CalendarConnectPanel, {
      props: {
        personId: "p1",
        calendarConnected: true,
        calendarProvider: "Google",
        onChanged,
      },
    });
    await fireEvent.click(
      screen.getByRole("button", { name: /calendar connected/i }),
    );
    await fireEvent.click(
      screen.getByRole("button", { name: /disconnect calendar/i }),
    );
    expect(confirmSpy).toHaveBeenCalled();
    expect(disconnect).toHaveBeenCalledWith("p1");
    expect(onChanged).toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it("Help section defaults to General info; clicking provider tabs swaps content + aria-selected", async () => {
    // Catches the regression where the tabs render but clicking them
    // doesn't actually change the visible content (state not wired).
    render(CalendarConnectPanel, {
      props: {
        personId: "p1",
        calendarConnected: false,
        calendarProvider: null,
        onChanged: vi.fn(),
      },
    });
    await fireEvent.click(
      screen.getByRole("button", { name: /connect calendar/i }),
    );

    const generalTab = screen.getByRole("tab", { name: /general info/i });
    expect(generalTab.getAttribute("aria-selected")).toBe("true");
    // General-tab specific copy: explanation of what a private subscription link is.
    expect(screen.getByText(/private subscription link/i)).toBeInTheDocument();

    const googleTab = screen.getByRole("tab", { name: /google/i });
    await fireEvent.click(googleTab);
    expect(googleTab.getAttribute("aria-selected")).toBe("true");
    expect(generalTab.getAttribute("aria-selected")).toBe("false");
    // Google-tab specific copy mentions the access permissions section.
    expect(
      screen.getByText(/access permissions for events/i),
    ).toBeInTheDocument();
    // Screenshot for that tab is rendered.
    const img = screen.getByAltText(/google calendar access permissions/i);
    expect(img.getAttribute("src")).toBe("/screenshots/google-calendar.png");
  });

  it("each provider tab references the correct screenshot path", async () => {
    // 404'd screenshots is the most common static-asset bug; pin every path.
    render(CalendarConnectPanel, {
      props: {
        personId: "p1",
        calendarConnected: false,
        calendarProvider: null,
        onChanged: vi.fn(),
      },
    });
    await fireEvent.click(
      screen.getByRole("button", { name: /connect calendar/i }),
    );

    await fireEvent.click(screen.getByRole("tab", { name: /apple/i }));
    expect(
      screen.getByAltText(/apple calendar share dialog/i).getAttribute("src"),
    ).toBe("/screenshots/apple-calendar.png");

    await fireEvent.click(screen.getByRole("tab", { name: /outlook/i }));
    expect(
      screen.getByAltText(/outlook publish a calendar/i).getAttribute("src"),
    ).toBe("/screenshots/outlook-calendar-publish.png");
    expect(screen.getByAltText(/outlook ics link/i).getAttribute("src")).toBe(
      "/screenshots/outlook-calendar-link.png",
    );
  });
});
