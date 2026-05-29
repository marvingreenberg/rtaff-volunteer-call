import { describe, expect, it } from "vitest";
import { confirmDialog, confirmState, resolveConfirm } from "./confirm.svelte";

describe("confirmDialog store", () => {
  it("returns true when resolveConfirm(true) is called", async () => {
    const promise = confirmDialog({ title: "T", body: "B" });
    expect(confirmState.pending).not.toBeNull();
    resolveConfirm(true);
    expect(await promise).toBe(true);
    expect(confirmState.pending).toBeNull();
  });

  it("returns false when resolveConfirm(false) is called", async () => {
    const promise = confirmDialog({ title: "T", body: "B" });
    resolveConfirm(false);
    expect(await promise).toBe(false);
  });

  it("cancels a prior pending dialog when a new request comes in", async () => {
    // Catch the first dialog being cancelled by the second one — this
    // protects against a callsite leaking confirms (e.g. fast double
    // click) where the older promise would otherwise hang forever.
    const first = confirmDialog({ title: "First", body: "B" });
    const second = confirmDialog({ title: "Second", body: "B" });
    expect(confirmState.pending?.title).toBe("Second");
    expect(await first).toBe(false);
    resolveConfirm(true);
    expect(await second).toBe(true);
  });

  it("preserves optional labels and danger flag on the pending request", () => {
    confirmDialog({
      title: "T",
      body: "B",
      okLabel: "Yes, do it",
      cancelLabel: "No, never",
      danger: true,
    });
    expect(confirmState.pending?.okLabel).toBe("Yes, do it");
    expect(confirmState.pending?.cancelLabel).toBe("No, never");
    expect(confirmState.pending?.danger).toBe(true);
    resolveConfirm(false);
  });

  it("resolveConfirm without a pending request is a safe no-op", () => {
    expect(confirmState.pending).toBeNull();
    expect(() => resolveConfirm(true)).not.toThrow();
  });
});
