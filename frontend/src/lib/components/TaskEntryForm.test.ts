import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import TaskEntryForm from "./TaskEntryForm.svelte";
import type { TaskCreate } from "$lib/api/client";

// Pin "now" so tests that hinge on the current date are stable regardless
// of when they run.
const PINNED_NOW = new Date(2026, 4, 5); // months are 0-indexed
const PINNED_YEAR = PINNED_NOW.getFullYear();

function lastValue(onchange: ReturnType<typeof vi.fn>): TaskCreate | null {
  const calls = onchange.mock.calls;
  if (calls.length === 0) return null;
  return calls[calls.length - 1][0] as TaskCreate | null;
}

function lastDirty(onchange: ReturnType<typeof vi.fn>): boolean {
  const calls = onchange.mock.calls;
  if (calls.length === 0) return false;
  return calls[calls.length - 1][1] as boolean;
}

async function fillRequiredFields(container: HTMLElement) {
  const date = container.querySelector(
    'input[placeholder="MM/DD"]',
  ) as HTMLInputElement;
  const address = container.querySelector(
    'input[placeholder="Address"]',
  ) as HTMLInputElement;
  const city = container.querySelector(
    'select[aria-label="City"]',
  ) as HTMLSelectElement;
  const description = container.querySelector(
    "textarea",
  ) as HTMLTextAreaElement;
  await fireEvent.input(date, { target: { value: "07/01" } });
  await fireEvent.input(address, { target: { value: "123 Oak St" } });
  await fireEvent.change(city, { target: { value: "Arlington" } });
  await fireEvent.input(description, { target: { value: "Fix gutters" } });
}

describe("TaskEntryForm", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(PINNED_NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not render a submit button (action buttons live in the parent)", () => {
    // The Add / Update buttons moved into TaskRow + the new-task header so
    // they can sit on the same row as the trash can. Catches a regression
    // that reintroduces an inline submit button (which would orphan-render
    // inside parents that use this form for inline composition).
    const { container } = render(TaskEntryForm, {
      props: { onchange: vi.fn() },
    });
    expect(
      container.querySelector('button[type="submit"]'),
    ).not.toBeInTheDocument();
  });

  it("emits onchange with null + dirty=false on initial render", () => {
    // Initial emit lets the parent set the action-button disabled state
    // without waiting for the first user keystroke. Catches a regression
    // where onchange only fires after typing.
    const onchange = vi.fn();
    render(TaskEntryForm, { props: { onchange } });
    expect(onchange).toHaveBeenCalled();
    expect(lastValue(onchange)).toBeNull();
    expect(lastDirty(onchange)).toBe(false);
  });

  it("emits a complete payload once all required fields are filled", async () => {
    const onchange = vi.fn();
    const { container } = render(TaskEntryForm, { props: { onchange } });
    await fillRequiredFields(container);
    expect(lastValue(onchange)).toEqual({
      short_description: "Fix gutters",
      date: `${PINNED_YEAR}-07-01`,
      time_start: "09:00",
      time_end: null,
      address: "123 Oak St",
      city: "Arlington",
      volunteers_needed: 4,
      skilled_needed: 0,
      notes: null,
      team_lead_id: null,
    });
    expect(lastDirty(onchange)).toBe(true);
  });

  it("renders city as a native <select> populated from CITIES", () => {
    // The city control is a native pull-down (no typeahead component).
    // Pinning that the city options come from the CITIES constant catches
    // a regression that swaps it back to a custom autocomplete.
    const { container } = render(TaskEntryForm, {
      props: { onchange: vi.fn() },
    });
    const citySelect = container.querySelector(
      'select[aria-label="City"]',
    ) as HTMLSelectElement;
    expect(citySelect).toBeInTheDocument();
    const optionLabels = Array.from(citySelect.options).map((o) => o.text);
    expect(optionLabels).toContain("Arlington");
    expect(optionLabels).toContain("Falls Church");
    // The first option is the empty placeholder so the select can read as
    // "unset" until the user picks one.
    expect(citySelect.options[0].value).toBe("");
  });

  it("team lead is a native <select> populated from the teamLeads prop", () => {
    // Same shape as city — native pull-down, no autocomplete. The list of
    // candidates comes from the parent (one fetch per page rather than per
    // row); pinning the prop wiring catches a regression that reverts to
    // an internal fetch + autocomplete.
    const { container } = render(TaskEntryForm, {
      props: {
        onchange: vi.fn(),
        teamLeads: [
          { id: "lead-1", first_name: "Pat", last_name: "Lee" },
          { id: "lead-2", first_name: "Sam", last_name: "Quinn" },
        ],
      },
    });
    const leadSelect = container.querySelector(
      'select[aria-label="Team lead"]',
    ) as HTMLSelectElement;
    expect(leadSelect).toBeInTheDocument();
    const labels = Array.from(leadSelect.options).map((o) => o.text);
    expect(labels).toEqual(["Team lead (optional)", "Pat Lee", "Sam Quinn"]);
  });

  it("picking a team lead emits team_lead_id in the payload", async () => {
    const onchange = vi.fn();
    const { container } = render(TaskEntryForm, {
      props: {
        onchange,
        teamLeads: [{ id: "lead-1", first_name: "Pat", last_name: "Lee" }],
      },
    });
    await fillRequiredFields(container);
    const leadSelect = container.querySelector(
      'select[aria-label="Team lead"]',
    ) as HTMLSelectElement;
    await fireEvent.change(leadSelect, { target: { value: "lead-1" } });
    expect(lastValue(onchange)).toMatchObject({ team_lead_id: "lead-1" });
  });

  it("emits null while a required field is missing", async () => {
    const onchange = vi.fn();
    const { container } = render(TaskEntryForm, { props: { onchange } });
    // Fill everything except city.
    const date = container.querySelector(
      'input[placeholder="MM/DD"]',
    ) as HTMLInputElement;
    const address = container.querySelector(
      'input[placeholder="Address"]',
    ) as HTMLInputElement;
    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;
    await fireEvent.input(date, { target: { value: "07/01" } });
    await fireEvent.input(address, { target: { value: "123 Oak St" } });
    await fireEvent.input(description, { target: { value: "Fix gutters" } });
    expect(lastValue(onchange)).toBeNull();
  });

  it("flags required fields with .invalid until they're filled", async () => {
    const { container } = render(TaskEntryForm, {
      props: { onchange: vi.fn() },
    });
    const date = container.querySelector(
      'input[placeholder="MM/DD"]',
    ) as HTMLInputElement;
    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;
    expect(date.classList.contains("invalid")).toBe(true);
    expect(description.classList.contains("invalid")).toBe(true);
    await fireEvent.input(date, { target: { value: "07/01" } });
    await fireEvent.input(description, { target: { value: "x" } });
    expect(date.classList.contains("invalid")).toBe(false);
    expect(description.classList.contains("invalid")).toBe(false);
  });

  it("populates from initial values for edit mode", () => {
    const { container } = render(TaskEntryForm, {
      props: {
        mode: "edit",
        onchange: vi.fn(),
        initial: {
          short_description: "Roof repair",
          date: "2026-08-15",
          time_start: "10:30",
          address: "456 Pine Ave",
          city: "Vienna",
          volunteers_needed: 6,
          skilled_needed: 2,
        },
      },
    });
    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;
    const date = container.querySelector(
      'input[placeholder="MM/DD"]',
    ) as HTMLInputElement;
    const time = screen.getByLabelText("Start time") as HTMLInputElement;
    const citySelect = container.querySelector(
      'select[aria-label="City"]',
    ) as HTMLSelectElement;
    const numbers = container.querySelectorAll(
      'input[type="number"]',
    ) as NodeListOf<HTMLInputElement>;
    expect(description.value).toBe("Roof repair");
    expect(date.value).toBe("08/15");
    expect(time.value).toBe("10:30 AM");
    expect(citySelect.value).toBe("Vienna");
    expect(numbers[0].value).toBe("6");
    expect(numbers[1].value).toBe("2");
  });

  it("preserves the original year when MM/DD is unchanged in edit mode", () => {
    const onchange = vi.fn();
    render(TaskEntryForm, {
      props: {
        mode: "edit",
        onchange,
        initial: {
          short_description: "Roof repair",
          date: "2024-08-15",
          address: "456 Pine Ave",
          city: "Vienna",
        },
      },
    });
    expect(lastValue(onchange)).toMatchObject({ date: "2024-08-15" });
    expect(lastDirty(onchange)).toBe(false);
  });

  it("uses the current year when MM/DD is changed in edit mode", async () => {
    const onchange = vi.fn();
    const { container } = render(TaskEntryForm, {
      props: {
        mode: "edit",
        onchange,
        initial: {
          short_description: "Roof repair",
          date: "2024-08-15",
          address: "456 Pine Ave",
          city: "Vienna",
        },
      },
    });
    const date = container.querySelector(
      'input[placeholder="MM/DD"]',
    ) as HTMLInputElement;
    await fireEvent.input(date, { target: { value: "09/01" } });
    expect(lastValue(onchange)).toMatchObject({ date: `${PINNED_YEAR}-09-01` });
    expect(lastDirty(onchange)).toBe(true);
  });

  it("rolls a past MM/DD into next year", async () => {
    // Now is May 5, 2026. February has already happened — assume 2027.
    const onchange = vi.fn();
    const { container } = render(TaskEntryForm, { props: { onchange } });
    const date = container.querySelector(
      'input[placeholder="MM/DD"]',
    ) as HTMLInputElement;
    const address = container.querySelector(
      'input[placeholder="Address"]',
    ) as HTMLInputElement;
    const citySelect = container.querySelector(
      'select[aria-label="City"]',
    ) as HTMLSelectElement;
    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;
    await fireEvent.input(date, { target: { value: "02/14" } });
    await fireEvent.input(address, { target: { value: "1 Main St" } });
    await fireEvent.change(citySelect, { target: { value: "Arlington" } });
    await fireEvent.input(description, { target: { value: "Snow removal" } });
    expect(lastValue(onchange)).toMatchObject({
      date: `${PINNED_YEAR + 1}-02-14`,
    });
  });

  it.each([
    ["9am", "09:00"],
    ["9:30am", "09:30"],
    ["1pm", "13:00"],
    ["12:00 PM", "12:00"],
    ["12am", "00:00"],
    ["13:30", "13:30"],
    ["09:00", "09:00"],
  ])("parses time %s as %s", async (input, expected) => {
    const onchange = vi.fn();
    const { container } = render(TaskEntryForm, { props: { onchange } });
    const time = screen.getByLabelText("Start time") as HTMLInputElement;
    await fireEvent.input(time, { target: { value: input } });
    await fillRequiredFields(container);
    expect(lastValue(onchange)).toMatchObject({ time_start: expected });
  });

  it("submits null time_start when the time field is empty or unparseable", async () => {
    const onchange = vi.fn();
    const { container } = render(TaskEntryForm, { props: { onchange } });
    const time = screen.getByLabelText("Start time") as HTMLInputElement;
    await fireEvent.input(time, { target: { value: "" } });
    await fillRequiredFields(container);
    expect(lastValue(onchange)).toMatchObject({ time_start: null });
  });

  it("auto-inserts '/' once a third digit is typed into MM/DD", async () => {
    const { container } = render(TaskEntryForm, {
      props: { onchange: vi.fn() },
    });
    const date = container.querySelector(
      'input[placeholder="MM/DD"]',
    ) as HTMLInputElement;
    await fireEvent.input(date, {
      target: { value: "05" },
      inputType: "insertText",
      data: "5",
    });
    expect(date.value).toBe("05");
    await fireEvent.input(date, {
      target: { value: "051" },
      inputType: "insertText",
      data: "1",
    });
    expect(date.value).toBe("05/1");
  });

  it("does not auto-insert '/' on paste or on deletion", async () => {
    const { container } = render(TaskEntryForm, {
      props: { onchange: vi.fn() },
    });
    const date = container.querySelector(
      'input[placeholder="MM/DD"]',
    ) as HTMLInputElement;
    await fireEvent.input(date, {
      target: { value: "0512" },
      inputType: "insertFromPaste",
      data: "0512",
    });
    expect(date.value).toBe("0512");
    await fireEvent.input(date, {
      target: { value: "051" },
      inputType: "deleteContentBackward",
      data: null,
    });
    expect(date.value).toBe("051");
  });
});
