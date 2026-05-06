import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/svelte";
import AutocompleteInput from "./AutocompleteInput.svelte";

// JSDOM doesn't implement scrollIntoView; Bits UI calls it when highlighting items
Element.prototype.scrollIntoView = vi.fn();

const mockItems = [
  { value: "1", label: "Alice Smith", description: "123 Main St" },
  { value: "2", label: "Bob Johnson", description: "456 Oak Ave" },
  { value: "3", label: "Alice Brown", description: "789 Pine Rd" },
];

describe("AutocompleteInput", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders input with placeholder", () => {
    const fetchOptions = vi.fn().mockResolvedValue([]);
    render(AutocompleteInput, {
      props: { fetchOptions, placeholder: "Search homeowners..." },
    });
    expect(
      screen.getByPlaceholderText("Search homeowners..."),
    ).toBeInTheDocument();
  });

  it("does not call fetchOptions with fewer than minChars characters", async () => {
    const fetchOptions = vi.fn().mockResolvedValue([]);
    render(AutocompleteInput, { props: { fetchOptions } });
    const input = screen.getByRole("combobox");
    await fireEvent.focus(input);
    await fireEvent.input(input, { target: { value: "Al" } });
    vi.advanceTimersByTime(400);
    expect(fetchOptions).not.toHaveBeenCalled();
  });

  it("calls fetchOptions immediately when minChars reached (no debounce)", async () => {
    const fetchOptions = vi.fn().mockResolvedValue([]);
    render(AutocompleteInput, { props: { fetchOptions } });
    const input = screen.getByRole("combobox");
    await fireEvent.focus(input);
    await fireEvent.input(input, { target: { value: "Ali" } });
    // Flush the microtask queue — no timer advance needed
    await vi.runAllTimersAsync();
    expect(fetchOptions).toHaveBeenCalledWith("Ali");
  });

  it("fetches with first minChars chars when typing past threshold quickly", async () => {
    const fetchOptions = vi.fn().mockResolvedValue([]);
    render(AutocompleteInput, { props: { fetchOptions } });
    const input = screen.getByRole("combobox");
    await fireEvent.focus(input);
    // Skip straight to 4 chars (simulating fast typing past threshold with no cache)
    await fireEvent.input(input, { target: { value: "Alic" } });
    vi.advanceTimersByTime(150);
    await vi.runAllTimersAsync();
    // Should fetch with first 3 chars, not "Alic"
    expect(fetchOptions).toHaveBeenCalledWith("Ali");
    expect(fetchOptions).not.toHaveBeenCalledWith("Alic");
  });

  it("renders dropdown items after fetch", async () => {
    const fetchOptions = vi.fn().mockResolvedValue(mockItems);
    render(AutocompleteInput, { props: { fetchOptions } });
    const input = screen.getByRole("combobox");
    await fireEvent.focus(input);
    await fireEvent.input(input, { target: { value: "Ali" } });
    await vi.runAllTimersAsync();
    // "Ali" matches Alice Smith and Alice Brown but not Bob Johnson (client-side filter)
    await waitFor(() => {
      expect(screen.getByText("Alice Smith")).toBeInTheDocument();
    });
    expect(screen.getByText("Alice Brown")).toBeInTheDocument();
    expect(screen.getByText("123 Main St")).toBeInTheDocument();
    expect(screen.queryByText("Bob Johnson")).not.toBeInTheDocument();
  });

  it("Enter key selects first item when dropdown is open", async () => {
    const fetchOptions = vi.fn().mockResolvedValue(mockItems);
    const onselect = vi.fn();
    render(AutocompleteInput, { props: { fetchOptions, onselect } });
    const input = screen.getByRole("combobox");
    await fireEvent.focus(input);
    await fireEvent.input(input, { target: { value: "Ali" } });
    await vi.runAllTimersAsync();
    await waitFor(() =>
      expect(screen.getByText("Alice Smith")).toBeInTheDocument(),
    );
    await fireEvent.keyDown(input, { key: "Enter" });
    expect(onselect).toHaveBeenCalledWith(
      expect.objectContaining({ value: "1", label: "Alice Smith" }),
    );
  });

  it("calls onselect when item clicked", async () => {
    const fetchOptions = vi.fn().mockResolvedValue(mockItems);
    const onselect = vi.fn();
    render(AutocompleteInput, { props: { fetchOptions, onselect } });
    const input = screen.getByRole("combobox");
    await fireEvent.focus(input);
    await fireEvent.input(input, { target: { value: "Ali" } });
    await vi.runAllTimersAsync();
    await waitFor(() => {
      expect(screen.getByText("Alice Smith")).toBeInTheDocument();
    });
    // Bits UI items use pointerup for selection; find item by role="option"
    const aliceItem = screen
      .getAllByRole("option")
      .find((el) => el.getAttribute("data-value") === "1")!;
    await fireEvent.pointerUp(aliceItem);
    expect(onselect).toHaveBeenCalledWith(
      expect.objectContaining({ value: "1", label: "Alice Smith" }),
    );
  });
});
