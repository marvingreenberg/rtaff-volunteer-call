import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import TaskEntryForm from "./TaskEntryForm.svelte";

// JSDOM doesn't implement scrollIntoView; bits-ui Combobox calls it.
Element.prototype.scrollIntoView = vi.fn();

// Pin "now" so tests that hinge on the current date are stable regardless
// of when they run. May 5, 2026 — late spring, so dates in Jul/Aug/etc. are
// in the future and dates in Jan/Feb roll forward to 2027.
const PINNED_NOW = new Date(2026, 4, 5); // months are 0-indexed
const PINNED_YEAR = PINNED_NOW.getFullYear();

describe("TaskEntryForm", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(PINNED_NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders required fields with red highlight when empty", () => {
    const { container } = render(TaskEntryForm, {
      props: { onsubmit: vi.fn() },
    });
    const date = container.querySelector(
      'input[placeholder="MM/DD"]',
    ) as HTMLInputElement;
    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;
    expect(date.classList.contains("invalid")).toBe(true);
    expect(description.classList.contains("invalid")).toBe(true);
  });

  it("populates defaults for time, volunteers, and skilled", () => {
    const { container } = render(TaskEntryForm, {
      props: { onsubmit: vi.fn() },
    });
    const time = screen.getByLabelText("Start time") as HTMLInputElement;
    const numbers = container.querySelectorAll(
      'input[type="number"]',
    ) as NodeListOf<HTMLInputElement>;
    expect(time.value).toBe("9:00 AM");
    expect(numbers[0].value).toBe("4");
    expect(numbers[1].value).toBe("0");
  });

  it("hides submit button until all required fields are filled", async () => {
    const onsubmit = vi.fn();
    const { container } = render(TaskEntryForm, { props: { onsubmit } });

    expect(
      container.querySelector('button[type="submit"]'),
    ).not.toBeInTheDocument();

    const date = container.querySelector(
      'input[placeholder="MM/DD"]',
    ) as HTMLInputElement;
    const address = container.querySelector(
      'input[placeholder="Address"]',
    ) as HTMLInputElement;
    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;
    const cityInput = screen.getByPlaceholderText("City") as HTMLInputElement;

    await fireEvent.input(date, { target: { value: "07/01" } });
    await fireEvent.input(address, { target: { value: "123 Oak St" } });
    await fireEvent.input(cityInput, { target: { value: "Arlington" } });
    expect(
      container.querySelector('button[type="submit"]'),
    ).not.toBeInTheDocument(); // description still missing

    await fireEvent.input(description, { target: { value: "Fix gutters" } });
    expect(
      container.querySelector('button[type="submit"]'),
    ).toBeInTheDocument();
  });

  it("clears the .invalid class once a required field is filled", async () => {
    const { container } = render(TaskEntryForm, {
      props: { onsubmit: vi.fn() },
    });
    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;
    expect(description.classList.contains("invalid")).toBe(true);
    await fireEvent.input(description, { target: { value: "x" } });
    expect(description.classList.contains("invalid")).toBe(false);
  });

  it("submits a normalized payload with defaults", async () => {
    const onsubmit = vi.fn();
    const { container } = render(TaskEntryForm, { props: { onsubmit } });

    const date = container.querySelector(
      'input[placeholder="MM/DD"]',
    ) as HTMLInputElement;
    const address = container.querySelector(
      'input[placeholder="Address"]',
    ) as HTMLInputElement;
    const cityInput = screen.getByPlaceholderText("City") as HTMLInputElement;
    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;

    await fireEvent.input(date, { target: { value: "07/01" } });
    await fireEvent.input(address, { target: { value: " 123 Oak St " } });
    await fireEvent.input(cityInput, { target: { value: " Arlington " } });
    await fireEvent.input(description, { target: { value: " Fix gutters " } });

    const submit = container.querySelector(
      'button[type="submit"]',
    ) as HTMLButtonElement;
    await fireEvent.click(submit);

    expect(onsubmit).toHaveBeenCalledWith({
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
  });

  it("does not render a submit button in edit mode", () => {
    const { container } = render(TaskEntryForm, {
      props: { mode: "edit", onchange: vi.fn() },
    });
    expect(
      container.querySelector('button[type="submit"]'),
    ).not.toBeInTheDocument();
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
    const cityInput = screen.getByPlaceholderText("City") as HTMLInputElement;
    const numbers = container.querySelectorAll(
      'input[type="number"]',
    ) as NodeListOf<HTMLInputElement>;

    expect(description.value).toBe("Roof repair");
    expect(date.value).toBe("08/15");
    expect(time.value).toBe("10:30 AM");
    expect(cityInput.value).toBe("Vienna");
    expect(numbers[0].value).toBe("6");
    expect(numbers[1].value).toBe("2");
  });

  it("preserves the original year when MM/DD is unchanged in edit mode", () => {
    // 2024 — deliberately not the current year.
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
    const lastCall = onchange.mock.calls[onchange.mock.calls.length - 1];
    expect(lastCall[0]).toMatchObject({ date: "2024-08-15" });
    expect(lastCall[1]).toBe(false); // dirty=false: nothing changed
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

    const lastCall = onchange.mock.calls[onchange.mock.calls.length - 1];
    expect(lastCall[0]).toMatchObject({ date: `${PINNED_YEAR}-09-01` });
    expect(lastCall[1]).toBe(true); // dirty
  });

  it("emits null value via onchange when the form is invalid", async () => {
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
    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;
    await fireEvent.input(description, { target: { value: "" } });

    const lastCall = onchange.mock.calls[onchange.mock.calls.length - 1];
    expect(lastCall[0]).toBe(null);
    expect(lastCall[1]).toBe(true); // dirty
  });

  it("rolls a past MM/DD into next year", async () => {
    // Now is May 5, 2026. February has already happened — assume 2027.
    const onsubmit = vi.fn();
    const { container } = render(TaskEntryForm, { props: { onsubmit } });

    const date = container.querySelector(
      'input[placeholder="MM/DD"]',
    ) as HTMLInputElement;
    const address = container.querySelector(
      'input[placeholder="Address"]',
    ) as HTMLInputElement;
    const cityInput = screen.getByPlaceholderText("City") as HTMLInputElement;
    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;

    await fireEvent.input(date, { target: { value: "02/14" } });
    await fireEvent.input(address, { target: { value: "1 Main St" } });
    await fireEvent.input(cityInput, { target: { value: "Arlington" } });
    await fireEvent.input(description, { target: { value: "Snow removal" } });

    const submit = container.querySelector(
      'button[type="submit"]',
    ) as HTMLButtonElement;
    await fireEvent.click(submit);

    expect(onsubmit).toHaveBeenCalledWith(
      expect.objectContaining({ date: `${PINNED_YEAR + 1}-02-14` }),
    );
  });

  it.each([
    ["9am", "09:00"],
    ["9:30am", "09:30"],
    ["1pm", "13:00"],
    ["12:00 PM", "12:00"],
    ["12am", "00:00"],
    ["13:30", "13:30"],
    ["09:00", "09:00"],
  ])("parses time %s as %s on submit", async (input, expected) => {
    const onsubmit = vi.fn();
    const { container } = render(TaskEntryForm, { props: { onsubmit } });

    const date = container.querySelector(
      'input[placeholder="MM/DD"]',
    ) as HTMLInputElement;
    const time = screen.getByLabelText("Start time") as HTMLInputElement;
    const address = container.querySelector(
      'input[placeholder="Address"]',
    ) as HTMLInputElement;
    const cityInput = screen.getByPlaceholderText("City") as HTMLInputElement;
    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;

    await fireEvent.input(date, { target: { value: "07/01" } });
    await fireEvent.input(time, { target: { value: input } });
    await fireEvent.input(address, { target: { value: "1 Main St" } });
    await fireEvent.input(cityInput, { target: { value: "Arlington" } });
    await fireEvent.input(description, { target: { value: "Task" } });

    const submit = container.querySelector(
      'button[type="submit"]',
    ) as HTMLButtonElement;
    await fireEvent.click(submit);

    expect(onsubmit).toHaveBeenCalledWith(
      expect.objectContaining({ time_start: expected }),
    );
  });

  it("submits null time_start when the time field is empty or unparseable", async () => {
    const onsubmit = vi.fn();
    const { container } = render(TaskEntryForm, { props: { onsubmit } });

    const date = container.querySelector(
      'input[placeholder="MM/DD"]',
    ) as HTMLInputElement;
    const time = screen.getByLabelText("Start time") as HTMLInputElement;
    const address = container.querySelector(
      'input[placeholder="Address"]',
    ) as HTMLInputElement;
    const cityInput = screen.getByPlaceholderText("City") as HTMLInputElement;
    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;

    await fireEvent.input(date, { target: { value: "07/01" } });
    await fireEvent.input(time, { target: { value: "" } });
    await fireEvent.input(address, { target: { value: "1 Main St" } });
    await fireEvent.input(cityInput, { target: { value: "Arlington" } });
    await fireEvent.input(description, { target: { value: "Task" } });

    const submit = container.querySelector(
      'button[type="submit"]',
    ) as HTMLButtonElement;
    await fireEvent.click(submit);

    expect(onsubmit).toHaveBeenCalledWith(
      expect.objectContaining({ time_start: null }),
    );
  });

  it("treats today as the current year (not next year)", async () => {
    const onsubmit = vi.fn();
    const { container } = render(TaskEntryForm, { props: { onsubmit } });

    const date = container.querySelector(
      'input[placeholder="MM/DD"]',
    ) as HTMLInputElement;
    const address = container.querySelector(
      'input[placeholder="Address"]',
    ) as HTMLInputElement;
    const cityInput = screen.getByPlaceholderText("City") as HTMLInputElement;
    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;

    // Pinned now is 05/05 — entering today's date should stay current year.
    await fireEvent.input(date, { target: { value: "05/05" } });
    await fireEvent.input(address, { target: { value: "1 Main St" } });
    await fireEvent.input(cityInput, { target: { value: "Arlington" } });
    await fireEvent.input(description, { target: { value: "Same-day fix" } });

    const submit = container.querySelector(
      'button[type="submit"]',
    ) as HTMLButtonElement;
    await fireEvent.click(submit);

    expect(onsubmit).toHaveBeenCalledWith(
      expect.objectContaining({ date: `${PINNED_YEAR}-05-05` }),
    );
  });
});
