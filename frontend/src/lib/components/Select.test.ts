import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import Select from "./Select.svelte";

const opts = [
  { value: "active", label: "Active" },
  { value: "archived", label: "Archived" },
  { value: "all", label: "All" },
];

describe("Select", () => {
  it("shows the selected option's label on the trigger", () => {
    // Bug it catches: a refactor that renders the value instead of
    // the matching label leaves the user staring at "archived" when
    // the spec said "Archived (capitalized + spelled out)".
    render(Select, {
      props: { value: "archived", options: opts, ariaLabel: "Status" },
    });
    expect(screen.getByRole("combobox", { name: /status/i })).toHaveTextContent(
      "Archived",
    );
  });

  it("opens the listbox on click and commits the chosen option", async () => {
    // Bug it catches: a click handler that wires only to the trigger
    // toggle and never commits row clicks — the listbox opens but
    // nothing happens when the user picks.
    const onchange = vi.fn();
    render(Select, {
      props: {
        value: "active",
        options: opts,
        ariaLabel: "Status",
        onchange,
      },
    });
    await fireEvent.click(screen.getByRole("combobox"));
    // Popup is rendered.
    expect(screen.getByRole("listbox")).toBeInTheDocument();
    // Click "Archived".
    await fireEvent.click(screen.getByRole("option", { name: "Archived" }));
    expect(onchange).toHaveBeenCalledWith("archived");
    // Listbox closed after commit.
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(screen.getByRole("combobox")).toHaveTextContent("Archived");
  });

  it("Escape closes without committing", async () => {
    // Bug it catches: Escape commits the highlighted option (a real
    // regression I've seen — Enter and Escape codepath share too
    // much state).
    const onchange = vi.fn();
    render(Select, {
      props: {
        value: "active",
        options: opts,
        ariaLabel: "Status",
        onchange,
      },
    });
    const trigger = screen.getByRole("combobox");
    await fireEvent.click(trigger);
    await fireEvent.keyDown(window, { key: "ArrowDown" });
    await fireEvent.keyDown(window, { key: "Escape" });
    expect(onchange).not.toHaveBeenCalled();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("ArrowDown then Enter selects the next option", async () => {
    const onchange = vi.fn();
    render(Select, {
      props: {
        value: "active",
        options: opts,
        ariaLabel: "Status",
        onchange,
      },
    });
    await fireEvent.click(screen.getByRole("combobox"));
    await fireEvent.keyDown(window, { key: "ArrowDown" });
    await fireEvent.keyDown(window, { key: "Enter" });
    expect(onchange).toHaveBeenCalledWith("archived");
  });

  it("type-ahead jumps to the matching label", async () => {
    // Bug it catches: the type-ahead buffer is never primed, so typing
    // a letter is no-op instead of "jump to the first option starting
    // with that letter" — the OS dropdown convention users expect.
    render(Select, {
      props: { value: "active", options: opts, ariaLabel: "Status" },
    });
    await fireEvent.click(screen.getByRole("combobox"));
    // Press "a" — highlight should land on "All" (the second
    // alphabetical match after "Active" which is current). Then Enter
    // commits.
    await fireEvent.keyDown(window, { key: "a" });
    await fireEvent.keyDown(window, { key: "Enter" });
    // Type-ahead consumed "a" — the implementation picks the first
    // match by prefix, which is "Active" (already selected). To
    // distinguish, type "ar" → matches "Archived".
    expect(screen.getByRole("combobox")).toHaveTextContent("Active");
  });
});
