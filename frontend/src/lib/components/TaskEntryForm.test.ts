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
  const description = container.querySelector(
    "textarea",
  ) as HTMLTextAreaElement;
  await fireEvent.input(date, { target: { value: "07/01" } });
  await fireEvent.input(address, { target: { value: "123 Oak St" } });
  await pickCombobox(container, "City", "Arlington");
  await fireEvent.input(description, { target: { value: "Fix gutters" } });
}

/** Drive the Select.svelte component: click trigger by aria-label,
 * then click the option whose visible label matches. */
async function pickCombobox(
  container: HTMLElement,
  ariaLabel: string,
  optionLabel: string,
): Promise<void> {
  const trigger = container.querySelector(
    `button[role="combobox"][aria-label="${ariaLabel}"]`,
  ) as HTMLButtonElement;
  if (!trigger) throw new Error(`No combobox with aria-label "${ariaLabel}"`);
  await fireEvent.click(trigger);
  const options = container.querySelectorAll<HTMLElement>('[role="option"]');
  const match = Array.from(options).find(
    (o) => o.textContent?.trim() === optionLabel,
  );
  if (!match) {
    throw new Error(
      `No option "${optionLabel}" in combobox "${ariaLabel}"; ` +
        `saw: ${Array.from(options)
          .map((o) => o.textContent?.trim())
          .join(", ")}`,
    );
  }
  await fireEvent.click(match);
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

  it("renders the city pulldown populated from CITIES with a placeholder", async () => {
    // The city control is a combobox component (Select.svelte). Pinning
    // that the options come from the CITIES constant catches a regression
    // that swaps it back to a freeform input or autocomplete.
    const { container } = render(TaskEntryForm, {
      props: { onchange: vi.fn() },
    });
    const trigger = container.querySelector(
      'button[role="combobox"][aria-label="City"]',
    ) as HTMLButtonElement;
    expect(trigger).toBeInTheDocument();
    // Trigger shows the "City" placeholder when nothing is picked.
    expect(trigger.textContent?.trim().startsWith("City")).toBe(true);
    await fireEvent.click(trigger);
    const optionLabels = Array.from(
      container.querySelectorAll('[role="option"]'),
    ).map((o) => o.textContent?.trim());
    expect(optionLabels).toContain("Arlington");
    expect(optionLabels).toContain("Falls Church");
  });

  it("team lead pulldown is populated from the teamLeads prop with a placeholder", async () => {
    const { container } = render(TaskEntryForm, {
      props: {
        onchange: vi.fn(),
        teamLeads: [
          { id: "lead-1", first_name: "Pat", last_name: "Lee" },
          { id: "lead-2", first_name: "Sam", last_name: "Quinn" },
        ],
      },
    });
    const trigger = container.querySelector(
      'button[role="combobox"][aria-label="Team lead"]',
    ) as HTMLButtonElement;
    expect(trigger).toBeInTheDocument();
    expect(trigger.textContent?.trim().startsWith("Team lead (optional)")).toBe(
      true,
    );
    await fireEvent.click(trigger);
    const labels = Array.from(
      container.querySelectorAll('[role="option"]'),
    ).map((o) => o.textContent?.trim());
    expect(labels).toEqual(["Pat Lee", "Sam Quinn"]);
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
    await pickCombobox(container, "Team lead", "Pat Lee");
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
    const cityTrigger = container.querySelector(
      'button[role="combobox"][aria-label="City"]',
    ) as HTMLButtonElement;
    const numbers = container.querySelectorAll(
      'input[type="number"]',
    ) as NodeListOf<HTMLInputElement>;
    expect(description.value).toBe("Roof repair");
    expect(date.value).toBe("08/15");
    expect(time.value).toBe("10:30 AM");
    // Trigger renders the selected city name (not the placeholder).
    expect(cityTrigger.textContent?.trim().startsWith("Vienna")).toBe(true);
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
    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;
    await fireEvent.input(date, { target: { value: "02/14" } });
    await fireEvent.input(address, { target: { value: "1 Main St" } });
    await pickCombobox(container, "City", "Arlington");
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
