import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import ListViewToggle from "./ListViewToggle.svelte";

describe("ListViewToggle", () => {
  it("renders two toggle buttons", () => {
    render(ListViewToggle, { props: { view: "pill", onchange: vi.fn() } });
    expect(screen.getByLabelText("Card view")).toBeInTheDocument();
    expect(screen.getByLabelText("Table view")).toBeInTheDocument();
  });

  it("marks pill button as active when view is pill", () => {
    render(ListViewToggle, { props: { view: "pill", onchange: vi.fn() } });
    expect(screen.getByLabelText("Card view")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByLabelText("Table view")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("marks table button as active when view is table", () => {
    render(ListViewToggle, { props: { view: "table", onchange: vi.fn() } });
    expect(screen.getByLabelText("Card view")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.getByLabelText("Table view")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("calls onchange with table when table button clicked", async () => {
    const onchange = vi.fn();
    render(ListViewToggle, { props: { view: "pill", onchange } });
    await fireEvent.click(screen.getByLabelText("Table view"));
    expect(onchange).toHaveBeenCalledWith("table");
  });

  it("calls onchange with pill when pill button clicked", async () => {
    const onchange = vi.fn();
    render(ListViewToggle, { props: { view: "table", onchange } });
    await fireEvent.click(screen.getByLabelText("Card view"));
    expect(onchange).toHaveBeenCalledWith("pill");
  });

  it("has accessible group role", () => {
    render(ListViewToggle, { props: { view: "pill", onchange: vi.fn() } });
    expect(screen.getByRole("group")).toHaveAttribute(
      "aria-label",
      "List view mode",
    );
  });
});
