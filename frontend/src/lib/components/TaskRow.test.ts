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

describe("TaskRow", () => {
  it("renders weekday + month + day in the summary", () => {
    render(TaskRow, {
      props: {
        task: makeTask({ date: "2026-07-01" }),
        expanded: false,
        ontoggle: vi.fn(),
        onchange: vi.fn(),
        ondelete: vi.fn(),
      },
    });
    expect(screen.getByText("Wednesday, July 1")).toBeInTheDocument();
  });

  it("shows volunteer count without slash when skilled is 0", () => {
    render(TaskRow, {
      props: {
        task: makeTask({ volunteers_needed: 4, skilled_needed: 0 }),
        expanded: false,
        ontoggle: vi.fn(),
        onchange: vi.fn(),
        ondelete: vi.fn(),
      },
    });
    expect(screen.getByText("(4)")).toBeInTheDocument();
  });

  it("shows volunteer/skilled count with slash when skilled > 0", () => {
    render(TaskRow, {
      props: {
        task: makeTask({ volunteers_needed: 4, skilled_needed: 1 }),
        expanded: false,
        ontoggle: vi.fn(),
        onchange: vi.fn(),
        ondelete: vi.fn(),
      },
    });
    expect(screen.getByText("(4/1)")).toBeInTheDocument();
  });

  it("renders the form only when expanded is true", () => {
    const { container, rerender } = render(TaskRow, {
      props: {
        task: makeTask(),
        expanded: false,
        ontoggle: vi.fn(),
        onchange: vi.fn(),
        ondelete: vi.fn(),
      },
    });
    expect(container.querySelector("form")).not.toBeInTheDocument();
    rerender({
      task: makeTask(),
      expanded: true,
      ontoggle: vi.fn(),
      onchange: vi.fn(),
      ondelete: vi.fn(),
    });
    expect(container.querySelector("form")).toBeInTheDocument();
  });

  it("calls ontoggle when the summary is clicked", async () => {
    const ontoggle = vi.fn();
    render(TaskRow, {
      props: {
        task: makeTask(),
        expanded: false,
        ontoggle,
        onchange: vi.fn(),
        ondelete: vi.fn(),
      },
    });
    await fireEvent.click(screen.getByRole("button", { expanded: false }));
    expect(ontoggle).toHaveBeenCalledTimes(1);
  });

  it("forwards form changes via onchange with the task id", async () => {
    const onchange = vi.fn();
    const { container } = render(TaskRow, {
      props: {
        task: makeTask(),
        expanded: true,
        ontoggle: vi.fn(),
        onchange,
        ondelete: vi.fn(),
      },
    });

    // Initial render fires onchange once with dirty=false.
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
    expect(lastCall[2]).toBe(true); // dirty
  });

  it("calls ondelete with the task id when the delete button is confirmed", async () => {
    const ondelete = vi.fn();
    const confirmSpy = vi
      .spyOn(window, "confirm")
      .mockImplementation(() => true);
    render(TaskRow, {
      props: {
        task: makeTask({ short_description: "Roof patch" }),
        expanded: true,
        ontoggle: vi.fn(),
        onchange: vi.fn(),
        ondelete,
      },
    });
    await fireEvent.click(screen.getByRole("button", { name: /delete task/i }));
    expect(confirmSpy).toHaveBeenCalled();
    expect(ondelete).toHaveBeenCalledWith("task-1");
    confirmSpy.mockRestore();
  });

  it("does not call ondelete when the confirm dialog is dismissed", async () => {
    const ondelete = vi.fn();
    const confirmSpy = vi
      .spyOn(window, "confirm")
      .mockImplementation(() => false);
    render(TaskRow, {
      props: {
        task: makeTask(),
        expanded: true,
        ontoggle: vi.fn(),
        onchange: vi.fn(),
        ondelete,
      },
    });
    await fireEvent.click(screen.getByRole("button", { name: /delete task/i }));
    expect(ondelete).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });
});
