import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import TaskRow from "./TaskRow.svelte";
import type { TaskResponse } from "$lib/api/client";

Element.prototype.scrollIntoView = vi.fn();

function makeTask(overrides: Partial<TaskResponse> = {}): TaskResponse {
  return {
    id: "task-1",
    volunteer_call_id: "call-1",
    short_description: "Install two lights, repair drywall",
    date: "2026-07-01",
    time_start: "09:00",
    time_end: null,
    address: "123 Oak St",
    city: "Alexandria",
    team_lead_id: null,
    team_lead_name: null,
    volunteers_needed: 4,
    skilled_needed: 0,
    status: "open",
    notes: null,
    assigned_count: 0,
    created_at: "2026-05-05T00:00:00Z",
    updated_at: "2026-05-05T00:00:00Z",
    ...overrides,
  };
}

function makeProps(overrides: Record<string, unknown> = {}) {
  return {
    task: makeTask(),
    expanded: false,
    ontoggle: vi.fn(),
    onchange: vi.fn(),
    onupdate: vi.fn(),
    ondelete: vi.fn(),
    ...overrides,
  };
}

describe("TaskRow", () => {
  it("renders weekday + month + day in the summary", () => {
    render(TaskRow, {
      props: makeProps({ task: makeTask({ date: "2026-07-01" }) }),
    });
    expect(screen.getByText("Wednesday, July 1")).toBeInTheDocument();
  });

  it("shows volunteer count without slash when skilled is 0", () => {
    render(TaskRow, {
      props: makeProps({
        task: makeTask({ volunteers_needed: 4, skilled_needed: 0 }),
      }),
    });
    expect(screen.getByText("(4)")).toBeInTheDocument();
  });

  it("shows volunteer/skilled count with slash when skilled > 0", () => {
    render(TaskRow, {
      props: makeProps({
        task: makeTask({ volunteers_needed: 4, skilled_needed: 1 }),
      }),
    });
    expect(screen.getByText("(4/1)")).toBeInTheDocument();
  });

  it("renders the form only when expanded is true", () => {
    const { container, rerender } = render(TaskRow, {
      props: makeProps(),
    });
    expect(container.querySelector("form")).not.toBeInTheDocument();
    rerender(makeProps({ expanded: true }));
    expect(container.querySelector("form")).toBeInTheDocument();
  });

  it("calls ontoggle when the summary is clicked", async () => {
    const ontoggle = vi.fn();
    render(TaskRow, { props: makeProps({ ontoggle }) });
    await fireEvent.click(screen.getByRole("button", { expanded: false }));
    expect(ontoggle).toHaveBeenCalledTimes(1);
  });

  it("forwards form changes via onchange with the task id", async () => {
    const onchange = vi.fn();
    const { container } = render(TaskRow, {
      props: makeProps({ expanded: true, onchange }),
    });

    expect(onchange).toHaveBeenCalled();
    expect(onchange.mock.calls[0][0]).toBe("task-1");
    expect(onchange.mock.calls[0][2]).toBe(false);

    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;
    await fireEvent.input(description, { target: { value: "Updated copy" } });

    const lastCall = onchange.mock.calls[onchange.mock.calls.length - 1];
    expect(lastCall[0]).toBe("task-1");
    expect(lastCall[1]).toMatchObject({
      short_description: "Updated copy",
      city: "Alexandria",
    });
    expect(lastCall[2]).toBe(true);
  });

  it("clicking the delete X does not toggle the row expand", async () => {
    // Regression: previously the delete control was inside the form panel.
    // The new X lives in the summary row alongside the toggle button, so
    // its click must stop propagation to avoid expanding/collapsing the row.
    const ontoggle = vi.fn();
    const ondelete = vi.fn();
    const confirmSpy = vi
      .spyOn(window, "confirm")
      .mockImplementation(() => false);
    render(TaskRow, { props: makeProps({ ontoggle, ondelete }) });
    await fireEvent.click(screen.getByRole("button", { name: /delete task/i }));
    expect(ontoggle).not.toHaveBeenCalled();
    expect(ondelete).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it("delete X confirm uses the formatted task date in its prompt", async () => {
    const ondelete = vi.fn();
    let promptedText = "";
    const confirmSpy = vi.spyOn(window, "confirm").mockImplementation((msg) => {
      promptedText = msg ?? "";
      return true;
    });
    render(TaskRow, {
      props: makeProps({
        task: makeTask({ date: "2026-07-01" }),
        ondelete,
      }),
    });
    await fireEvent.click(screen.getByRole("button", { name: /delete task/i }));
    expect(promptedText).toContain("Wednesday, July 1");
    expect(ondelete).toHaveBeenCalledWith("task-1");
    confirmSpy.mockRestore();
  });

  it("does not call ondelete when the confirm dialog is dismissed", async () => {
    const ondelete = vi.fn();
    const confirmSpy = vi
      .spyOn(window, "confirm")
      .mockImplementation(() => false);
    render(TaskRow, { props: makeProps({ expanded: true, ondelete }) });
    await fireEvent.click(screen.getByRole("button", { name: /delete task/i }));
    expect(ondelete).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it("forwards Update click via onupdate with the task id and payload", async () => {
    // Without this wiring, clicking Update in the embedded TaskEntryForm
    // would have no effect — the row is the bridge between the form and
    // the parent route's save handler.
    const onupdate = vi.fn();
    const { container } = render(TaskRow, {
      props: makeProps({ expanded: true, onupdate }),
    });

    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;
    await fireEvent.input(description, { target: { value: "Rewired text" } });

    const updateBtn = screen.getByRole("button", { name: /^Update / });
    await fireEvent.click(updateBtn);

    expect(onupdate).toHaveBeenCalledTimes(1);
    expect(onupdate.mock.calls[0][0]).toBe("task-1");
    expect(onupdate.mock.calls[0][1]).toMatchObject({
      short_description: "Rewired text",
    });
  });
});
