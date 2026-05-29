import { describe, expect, it, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import TaskRow from "./TaskRow.svelte";

const baseProps = {
  name: "Driftwood collection",
  summary: "Stage driftwood pulled from the upper beach into the sort pile…",
  description:
    "Stage driftwood pulled from the upper beach into the sort pile by the lot.\n\nAnything over 6 ft. goes to the structural side.",
  city: "Pacifica",
  date: "Sat Jun 21",
  checked: false,
  expanded: false,
};

describe("TaskRow", () => {
  it("renders the summary text in the .task-summary slot when collapsed", () => {
    const { container } = render(TaskRow, { props: baseProps });
    const summary = container.querySelector(".task-summary") as HTMLElement;
    expect(summary).not.toBeNull();
    expect(summary.textContent).toContain(
      "Stage driftwood pulled from the upper beach",
    );
  });

  it("collapsed: .task wrapper does NOT carry .expanded (CSS hides the detail dl)", () => {
    const { container } = render(TaskRow, { props: baseProps });
    const li = container.querySelector("li.task") as HTMLElement;
    expect(li.classList.contains("expanded")).toBe(false);
  });

  it("expanded: .task wrapper carries .expanded and the description renders in .task-description", () => {
    const { container } = render(TaskRow, {
      props: { ...baseProps, expanded: true },
    });
    const li = container.querySelector("li.task") as HTMLElement;
    expect(li.classList.contains("expanded")).toBe(true);
    const desc = container.querySelector(".task-description") as HTMLElement;
    expect(desc.textContent).toContain("structural side");
  });

  it("does NOT show time in the collapsed meta (lives in expanded detail only)", () => {
    const props = { ...baseProps, time: "10:00–13:00" };
    const { container } = render(TaskRow, { props });
    const meta = container.querySelector(".task-meta")!;
    expect(meta.textContent).not.toContain("10:00");
  });

  it("renders time inside .task-detail when expanded", () => {
    const { container } = render(TaskRow, {
      props: { ...baseProps, expanded: true, time: "10:00–13:00" },
    });
    const detail = container.querySelector(".task-detail") as HTMLElement;
    expect(detail.textContent).toContain("10:00");
  });

  it("fires onToggleChecked when the checkbox changes", async () => {
    const onToggleChecked = vi.fn();
    const { container } = render(TaskRow, {
      props: { ...baseProps, onToggleChecked },
    });
    const cb = container.querySelector(
      "input[type=checkbox]",
    ) as HTMLInputElement;
    await fireEvent.click(cb);
    expect(onToggleChecked).toHaveBeenCalledOnce();
  });

  it("fires onToggleExpanded when the row body is clicked", async () => {
    const onToggleExpanded = vi.fn();
    const { container } = render(TaskRow, {
      props: { ...baseProps, onToggleExpanded },
    });
    const body = container.querySelector(".task-body") as HTMLElement;
    await fireEvent.click(body);
    expect(onToggleExpanded).toHaveBeenCalledOnce();
  });

  it("renders the conflict pill only when conflict=true", () => {
    const { container, rerender } = render(TaskRow, { props: baseProps });
    expect(container.querySelector(".conflict-flag")).toBeNull();
    rerender({
      ...baseProps,
      conflict: true,
      conflictTitle: "Overlaps with X",
    });
    const flag = container.querySelector(".conflict-flag") as HTMLElement;
    expect(flag).not.toBeNull();
    expect(flag.getAttribute("title")).toBe("Overlaps with X");
  });
});
