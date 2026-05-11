import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import TaskRow from "./TaskRow.svelte";
import type { TaskResponse } from "$lib/api/client";

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
    teamLeads: [],
    ontoggle: vi.fn(),
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

  it("shows the trash glyph (not an ×)", () => {
    // User explicitly asked for a trash can, not an X. Pin both directions
    // so a stylistic regression to "×" gets caught.
    render(TaskRow, { props: makeProps() });
    const trash = screen.getByRole("button", { name: /delete task/i });
    expect(trash.textContent?.trim()).toBe("🗑️");
    expect(trash.textContent?.trim()).not.toBe("×");
  });

  it("only renders the Update button when expanded", () => {
    const { rerender } = render(TaskRow, { props: makeProps() });
    expect(
      screen.queryByRole("button", { name: /update task/i }),
    ).not.toBeInTheDocument();
    rerender(makeProps({ expanded: true }));
    expect(
      screen.getByRole("button", { name: /update task/i }),
    ).toBeInTheDocument();
  });

  it("Update is disabled until the form is dirty AND valid", async () => {
    // Without dirty-gating, Update would be active the moment the row
    // opens (since the task is already valid). Without valid-gating, the
    // user could wipe a required field and still click Update, which would
    // silently fail or persist garbage.
    const { container } = render(TaskRow, {
      props: makeProps({ expanded: true }),
    });
    const update = screen.getByRole("button", { name: /update task/i });
    expect(update).toBeDisabled();

    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;
    await fireEvent.input(description, { target: { value: "Roof rebuild" } });
    expect(update).not.toBeDisabled();

    // Wipe a required field → Update goes back to disabled.
    await fireEvent.input(description, { target: { value: "" } });
    expect(update).toBeDisabled();
  });

  it("clicking Update fires onupdate(taskId, payload)", async () => {
    const onupdate = vi.fn();
    const { container } = render(TaskRow, {
      props: makeProps({ expanded: true, onupdate }),
    });
    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;
    await fireEvent.input(description, { target: { value: "Rewired text" } });
    await fireEvent.click(screen.getByRole("button", { name: /update task/i }));
    expect(onupdate).toHaveBeenCalledTimes(1);
    expect(onupdate.mock.calls[0][0]).toBe("task-1");
    expect(onupdate.mock.calls[0][1]).toMatchObject({
      short_description: "Rewired text",
    });
  });

  it("clicking the trash does not toggle the row expand", async () => {
    // The trash sits in the summary row alongside the toggle button; its
    // click handler stops propagation so trash-confirmed-cancel doesn't
    // accidentally fold/unfold the row.
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

  it("trash confirm uses the formatted task date in its prompt", async () => {
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

  it("collapsing the row clears in-flight edits (Update becomes disabled on reopen)", async () => {
    // Closing without clicking Update discards the changes — pin that
    // the pending payload + dirty flag don't survive a collapse/reopen.
    const onupdate = vi.fn();
    const { container, rerender } = render(TaskRow, {
      props: makeProps({ expanded: true, onupdate }),
    });
    const description = container.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;
    await fireEvent.input(description, { target: { value: "Changed" } });
    expect(
      screen.getByRole("button", { name: /update task/i }),
    ).not.toBeDisabled();

    rerender(makeProps({ expanded: false, onupdate }));
    rerender(makeProps({ expanded: true, onupdate }));
    expect(screen.getByRole("button", { name: /update task/i })).toBeDisabled();
  });
});
