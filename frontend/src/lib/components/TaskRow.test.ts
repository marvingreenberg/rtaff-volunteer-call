import { describe, expect, it, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import TaskRow from "./TaskRow.svelte";

const baseProps = {
  description:
    "Stage driftwood pulled from the upper beach into the sort pile by the lot.\n\nAnything over 6 ft. goes to the structural side.",
  city: "Pacifica",
  date: "Sat Jun 21",
  checked: false,
  expanded: false,
};

describe("TaskRow", () => {
  it("renders the derived 65-char summary when collapsed", () => {
    const { container } = render(TaskRow, { props: baseProps });
    const summary = container.querySelector(".task-summary") as HTMLElement;
    expect(summary).not.toBeNull();
    expect(summary.textContent!.endsWith("…")).toBe(true);
    expect(summary.textContent!.length).toBeLessThanOrEqual(66);
    expect(summary.textContent!).toContain(
      "Stage driftwood pulled from the upper beach",
    );
  });

  it("does not append an ellipsis when description fits within 65 chars", () => {
    const { container } = render(TaskRow, {
      props: { ...baseProps, description: "Short and sweet." },
    });
    const summary = container.querySelector(".task-summary") as HTMLElement;
    expect(summary.textContent).toBe("Short and sweet.");
  });

  it("collapsed: .task wrapper does NOT carry .expanded (CSS hides the detail dl)", () => {
    const { container } = render(TaskRow, { props: baseProps });
    const li = container.querySelector("li.task") as HTMLElement;
    expect(li.classList.contains("expanded")).toBe(false);
  });

  it("expanded: .task wrapper carries .expanded and the full description renders in .task-description", () => {
    const { container } = render(TaskRow, {
      props: { ...baseProps, expanded: true },
    });
    const li = container.querySelector("li.task") as HTMLElement;
    expect(li.classList.contains("expanded")).toBe(true);
    const desc = container.querySelector(".task-description") as HTMLElement;
    expect(desc.textContent).toContain("structural side");
  });

  it("hides .task-description in expanded view when description fits in the summary (would duplicate the headline)", () => {
    const { container } = render(TaskRow, {
      props: { ...baseProps, expanded: true, description: "Roof patch" },
    });
    const li = container.querySelector("li.task") as HTMLElement;
    expect(li.classList.contains("expanded")).toBe(true);
    // The summary headline is "Roof patch"; rendering it again in
    // .task-description would visually duplicate it. The guard must skip it.
    expect(container.querySelector(".task-description")).toBeNull();
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

  it("fires onToggleExpanded on Enter keydown in the body", async () => {
    const onToggleExpanded = vi.fn();
    const { container } = render(TaskRow, {
      props: { ...baseProps, onToggleExpanded },
    });
    const body = container.querySelector(".task-body") as HTMLElement;
    await fireEvent.keyDown(body, { key: "Enter" });
    expect(onToggleExpanded).toHaveBeenCalledOnce();
  });

  it("fires onToggleExpanded on Space keydown in the body and prevents page scroll", async () => {
    const onToggleExpanded = vi.fn();
    const { container } = render(TaskRow, {
      props: { ...baseProps, onToggleExpanded },
    });
    const body = container.querySelector(".task-body") as HTMLElement;
    const event = new KeyboardEvent("keydown", {
      key: " ",
      cancelable: true,
      bubbles: true,
    });
    body.dispatchEvent(event);
    expect(onToggleExpanded).toHaveBeenCalledOnce();
    expect(event.defaultPrevented).toBe(true);
  });

  it("fires onToggleExpanded when the chevron button is clicked", async () => {
    const onToggleExpanded = vi.fn();
    const { container } = render(TaskRow, {
      props: { ...baseProps, onToggleExpanded },
    });
    const expand = container.querySelector(".task-expand") as HTMLButtonElement;
    await fireEvent.click(expand);
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
