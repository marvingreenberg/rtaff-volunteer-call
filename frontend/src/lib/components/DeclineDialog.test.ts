import { describe, expect, it, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import DeclineDialog from "./DeclineDialog.svelte";

describe("DeclineDialog", () => {
  it("renders nothing when closed", () => {
    const { container } = render(DeclineDialog, {
      props: { open: false, onConfirm: vi.fn(), onCancel: vi.fn() },
    });
    expect(container.querySelector("dialog")).toBeNull();
  });

  it("pre-fills the note with the team lead's name and date", () => {
    const { getByLabelText } = render(DeclineDialog, {
      props: {
        open: true,
        taskDescription: "Replace ceiling fan",
        teamLeadName: "Bard Jackson",
        dateLabel: "Monday, June 1",
        onConfirm: vi.fn(),
        onCancel: vi.fn(),
      },
    });
    const textarea = getByLabelText(
      "Note to your team lead",
    ) as HTMLTextAreaElement;
    expect(textarea.value).toBe(
      "Sorry Bard Jackson, I'm unable to come to the project on Monday, June 1.",
    );
  });

  it("confirms with the edited message", async () => {
    const onConfirm = vi.fn();
    const { getByLabelText, getByText } = render(DeclineDialog, {
      props: {
        open: true,
        taskDescription: "Task",
        teamLeadName: "Lee",
        dateLabel: "Monday, June 1",
        onConfirm,
        onCancel: vi.fn(),
      },
    });
    const textarea = getByLabelText(
      "Note to your team lead",
    ) as HTMLTextAreaElement;
    await fireEvent.input(textarea, {
      target: { value: "Family emergency, sorry." },
    });
    await fireEvent.click(getByText("Decline & notify"));
    expect(onConfirm).toHaveBeenCalledWith("Family emergency, sorry.");
  });

  it("cancels without confirming", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    const { getByText } = render(DeclineDialog, {
      props: {
        open: true,
        taskDescription: "Task",
        teamLeadName: null,
        dateLabel: "Monday, June 1",
        onConfirm,
        onCancel,
      },
    });
    await fireEvent.click(getByText("Keep my assignment"));
    expect(onCancel).toHaveBeenCalled();
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
