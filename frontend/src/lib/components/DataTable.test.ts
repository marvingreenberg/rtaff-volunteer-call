import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import DataTable from "./DataTable.svelte";
import type { Column } from "./data-table";

const columns: Column[] = [
  { key: "name", label: "Name", getValue: (item) => item.name as string },
  {
    key: "count",
    label: "Count",
    getValue: (item) => item.count as number,
    align: "right",
  },
  {
    key: "status",
    label: "Status",
    getValue: (item) => item.status as string,
    sortable: false,
  },
];

const items = [
  { name: "Alice", count: 3, status: "active" },
  { name: "Bob", count: 1, status: "pending" },
];

describe("DataTable", () => {
  it("renders column headers", () => {
    render(DataTable, { props: { items, columns } });
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Count")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
  });

  it("renders cell values", () => {
    render(DataTable, { props: { items, columns } });
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("calls onsort when clicking a sortable header", async () => {
    const onsort = vi.fn();
    render(DataTable, { props: { items, columns, onsort } });
    await fireEvent.click(screen.getByText("Name"));
    expect(onsort).toHaveBeenCalledWith("name", "asc");
  });

  it("does not call onsort for non-sortable columns", async () => {
    const onsort = vi.fn();
    render(DataTable, { props: { items, columns, onsort } });
    // Status is not sortable, rendered as plain span not button
    const statusHeader = screen.getByText("Status");
    await fireEvent.click(statusHeader);
    expect(onsort).not.toHaveBeenCalled();
  });

  it("cycles sort direction: asc -> desc -> clear", async () => {
    const onsort = vi.fn();
    render(DataTable, {
      props: { items, columns, sortKey: "name", sortDir: "asc", onsort },
    });
    // Already asc, clicking should go to desc
    await fireEvent.click(screen.getByText("Name"));
    expect(onsort).toHaveBeenCalledWith("name", "desc");
  });

  it("clears sort on third click of same column", async () => {
    const onsort = vi.fn();
    render(DataTable, {
      props: { items, columns, sortKey: "name", sortDir: "desc", onsort },
    });
    await fireEvent.click(screen.getByText("Name"));
    expect(onsort).toHaveBeenCalledWith("", "asc");
  });

  it("shows sort arrow for sorted column", () => {
    const { container } = render(DataTable, {
      props: { items, columns, sortKey: "name", sortDir: "asc" },
    });
    const arrow = container.querySelector(".sort-arrow");
    expect(arrow).not.toBeNull();
    expect(arrow!.textContent).toContain("\u25B2");
  });

  it("truncates long cell values and adds title", () => {
    const truncCols: Column[] = [
      {
        key: "desc",
        label: "Desc",
        getValue: (item) => item.desc as string,
        truncate: 5,
      },
    ];
    const longItems = [{ desc: "Hello World" }];
    const { container } = render(DataTable, {
      props: { items: longItems, columns: truncCols },
    });
    const td = container.querySelector("td");
    expect(td!.textContent).toContain("Hello\u2026");
    expect(td!.getAttribute("title")).toBe("Hello World");
  });

  it("does not add title when text is not truncated", () => {
    const truncCols: Column[] = [
      {
        key: "desc",
        label: "Desc",
        getValue: (item) => item.desc as string,
        truncate: 50,
      },
    ];
    const shortItems = [{ desc: "Short" }];
    const { container } = render(DataTable, {
      props: { items: shortItems, columns: truncCols },
    });
    const td = container.querySelector("td");
    expect(td!.getAttribute("title")).toBeNull();
  });
});
