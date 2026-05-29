import { describe, expect, it, beforeEach } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import ConfirmDialogHost from "./ConfirmDialogHost.svelte";
import {
  confirmDialog,
  confirmState,
  resolveConfirm,
} from "$lib/stores/confirm.svelte";

beforeEach(() => {
  if (confirmState.pending) resolveConfirm(false);
});

describe("ConfirmDialogHost", () => {
  it("renders nothing when there is no pending request", () => {
    const { container } = render(ConfirmDialogHost);
    expect(container.querySelector("dialog")).toBeNull();
  });

  it("renders title, body, and default labels when a request is pending", async () => {
    const { getByText, findByText } = render(ConfirmDialogHost);
    confirmDialog({ title: "Delete it?", body: "This cannot be undone." });
    await findByText("Delete it?");
    expect(getByText("This cannot be undone.")).toBeInTheDocument();
    expect(getByText("OK")).toBeInTheDocument();
    expect(getByText("Cancel")).toBeInTheDocument();
  });

  it("resolves true when OK is clicked", async () => {
    const { findByText } = render(ConfirmDialogHost);
    const promise = confirmDialog({ title: "T", body: "B" });
    const ok = await findByText("OK");
    await fireEvent.click(ok);
    expect(await promise).toBe(true);
  });

  it("resolves false when Cancel is clicked", async () => {
    const { findByText } = render(ConfirmDialogHost);
    const promise = confirmDialog({ title: "T", body: "B" });
    const cancel = await findByText("Cancel");
    await fireEvent.click(cancel);
    expect(await promise).toBe(false);
  });

  it("uses role=alertdialog and .btn-danger on the OK button when danger=true", async () => {
    const { container, findByText } = render(ConfirmDialogHost);
    confirmDialog({ title: "T", body: "B", danger: true });
    await findByText("OK");
    const dialog = container.querySelector("dialog")!;
    expect(dialog.getAttribute("role")).toBe("alertdialog");
    const okBtn = container.querySelector(".btn-danger");
    expect(okBtn).not.toBeNull();
    expect(okBtn?.textContent?.trim()).toBe("OK");
    resolveConfirm(false);
  });

  it("honors okLabel / cancelLabel overrides", async () => {
    const { findByText } = render(ConfirmDialogHost);
    confirmDialog({
      title: "T",
      body: "B",
      okLabel: "Yes, do it",
      cancelLabel: "Never mind",
    });
    await findByText("Yes, do it");
    await findByText("Never mind");
    resolveConfirm(false);
  });
});
