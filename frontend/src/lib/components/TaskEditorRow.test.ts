import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import TaskEditorRow from "./TaskEditorRow.svelte";
import type { TaskResponse } from "$lib/api/client";
// vi.mock calls are hoisted above imports at runtime by Vitest, so the
// confirmDialog import below resolves to the mocked module.
import { confirmDialog } from "$lib/stores/confirm.svelte";

vi.mock("$lib/stores/confirm.svelte", () => ({
  confirmDialog: vi.fn(),
}));

const confirmMock = confirmDialog as ReturnType<typeof vi.fn>;

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
    assignees: [],
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

describe("TaskEditorRow", () => {
  it("renders weekday + month + day in the summary", () => {
    render(TaskEditorRow, {
      props: makeProps({ task: makeTask({ date: "2026-07-01" }) }),
    });
    expect(screen.getByText("Wednesday, July 1")).toBeInTheDocument();
  });

  it("shows the trash glyph (not an ×)", () => {
    // User explicitly asked for a trash can, not an X. Pin both directions
    // so a stylistic regression to "×" gets caught.
    render(TaskEditorRow, { props: makeProps() });
    const trash = screen.getByRole("button", { name: /delete task/i });
    expect(trash.textContent?.trim()).toBe("🗑️");
    expect(trash.textContent?.trim()).not.toBe("×");
  });

  it("only renders the Update button when expanded", () => {
    const { rerender } = render(TaskEditorRow, { props: makeProps() });
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
    const { container } = render(TaskEditorRow, {
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
    const { container } = render(TaskEditorRow, {
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
    confirmMock.mockResolvedValue(false);
    render(TaskEditorRow, { props: makeProps({ ontoggle, ondelete }) });
    await fireEvent.click(screen.getByRole("button", { name: /delete task/i }));
    expect(ontoggle).not.toHaveBeenCalled();
    expect(ondelete).not.toHaveBeenCalled();
  });

  it("trash confirm uses the formatted task date in its body", async () => {
    const ondelete = vi.fn();
    confirmMock.mockResolvedValue(true);
    render(TaskEditorRow, {
      props: makeProps({
        task: makeTask({ date: "2026-07-01" }),
        ondelete,
      }),
    });
    await fireEvent.click(screen.getByRole("button", { name: /delete task/i }));
    // confirmDialog is awaited inside the handler; settle the microtask queue.
    await Promise.resolve();
    expect(confirmMock).toHaveBeenCalled();
    const arg = confirmMock.mock.calls.at(-1)?.[0];
    expect(arg?.body).toContain("Wednesday, July 1");
    expect(ondelete).toHaveBeenCalledWith("task-1");
  });

  it("renders assignee chips with team-lead marker", () => {
    // Bug it catches: the assignee chip block silently skips
    // is_team_lead, so the admin can't see at a glance who's leading.
    render(TaskEditorRow, {
      props: makeProps({
        task: makeTask({
          assignees: [
            {
              person_id: "p1",
              first_name: "Ada",
              last_name: "Lovelace",
              initials: "AL",
              is_team_lead: true,
            },
            {
              person_id: "p2",
              first_name: "Bob",
              last_name: "Test",
              initials: "BT",
              is_team_lead: false,
            },
          ],
        }),
      }),
    });
    const lead = screen.getByText("AL");
    const crew = screen.getByText("BT");
    expect(lead).toHaveClass("assignee-lead");
    expect(crew).not.toHaveClass("assignee-lead");
  });

  it("renders no chip block when assignees is empty", () => {
    // Bug it catches: the {#if assignees && length} guard is dropped,
    // so an empty list paints a stray container with no contents.
    const { container } = render(TaskEditorRow, {
      props: makeProps({ task: makeTask({ assignees: [] }) }),
    });
    expect(container.querySelector(".assignees")).toBeNull();
  });

  it("does not call ondelete when the confirm dialog is dismissed", async () => {
    const ondelete = vi.fn();
    confirmMock.mockResolvedValue(false);
    render(TaskEditorRow, { props: makeProps({ expanded: true, ondelete }) });
    await fireEvent.click(screen.getByRole("button", { name: /delete task/i }));
    await Promise.resolve();
    expect(ondelete).not.toHaveBeenCalled();
  });

  it("collapsing the row clears in-flight edits (Update becomes disabled on reopen)", async () => {
    // Closing without clicking Update discards the changes — pin that
    // the pending payload + dirty flag don't survive a collapse/reopen.
    const onupdate = vi.fn();
    const { container, rerender } = render(TaskEditorRow, {
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
