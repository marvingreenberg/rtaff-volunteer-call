<script lang="ts">
  // Confirmation modal for a volunteer declining an assigned task. Controlled
  // by the parent via `open`; emits the (editable, pre-filled) message on
  // confirm. Mirrors ConfirmDialogHost's native-<dialog> approach for focus
  // trapping, Esc-to-close, and a styled backdrop.
  import { declineMessagePrefill } from "$lib/utils/decline";

  let {
    open = false,
    taskDescription = "",
    teamLeadName = null,
    dateLabel = "",
    onConfirm,
    onCancel,
  }: {
    open?: boolean;
    taskDescription?: string;
    teamLeadName?: string | null;
    dateLabel?: string;
    onConfirm: (message: string) => void;
    onCancel: () => void;
  } = $props();

  let dialogEl: HTMLDialogElement | null = $state(null);
  let message = $state("");
  let wasOpen = false;

  // Re-seed the message each time the dialog opens (not on every keystroke,
  // so the volunteer's edits survive), and drive the native modal open/close.
  $effect(() => {
    if (open && !wasOpen) {
      message = declineMessagePrefill(teamLeadName, dateLabel);
    }
    wasOpen = open;

    if (!dialogEl) return;
    if (open) {
      if (typeof dialogEl.showModal === "function" && !dialogEl.open) {
        dialogEl.showModal();
      }
    } else if (typeof dialogEl.close === "function" && dialogEl.open) {
      dialogEl.close();
    }
  });

  function onClose() {
    // Esc / backdrop / programmatic close: treat as cancel if still open.
    if (open) onCancel();
  }

  function onBackdropClick(e: MouseEvent) {
    if (e.target === dialogEl) onCancel();
  }
</script>

{#if open}
  <dialog
    bind:this={dialogEl}
    onclose={onClose}
    onclick={onBackdropClick}
    role="alertdialog"
    aria-labelledby="decline-title"
    aria-describedby="decline-body"
    class="danger"
  >
    <div class="surface">
      <h2 id="decline-title">Decline this task?</h2>
      <p id="decline-body">
        This notifies your team lead and the coordinator that you can no longer do
        <strong>{taskDescription}</strong>. Add a note for your team lead:
      </p>
      <textarea bind:value={message} rows="4" aria-label="Note to your team lead"></textarea>
      <div class="actions">
        <button type="button" class="btn btn-secondary" onclick={() => onCancel()}>
          Keep my assignment
        </button>
        <button type="button" class="btn btn-danger" onclick={() => onConfirm(message)}>
          Decline &amp; notify
        </button>
      </div>
    </div>
  </dialog>
{/if}

<style>
  dialog {
    padding: 0;
    border: 0;
    background: transparent;
    color: inherit;
    max-width: min(480px, calc(100vw - var(--sp-5) * 2));
    border-radius: var(--radius);
    overflow: visible;
  }
  dialog::backdrop {
    background: rgba(30, 47, 61, 0.45);
    backdrop-filter: blur(2px);
    -webkit-backdrop-filter: blur(2px);
  }
  .surface {
    background: var(--surface-1);
    border: 1px solid var(--hairline);
    border-radius: var(--radius);
    padding: var(--sp-5) var(--sp-5) var(--sp-4);
    box-shadow: 0 24px 60px -24px rgba(30, 47, 61, 0.4);
  }
  h2 {
    margin: 0 0 var(--sp-3) 0;
    font-family: var(--font-display);
    font-weight: var(--heading-weight);
    font-size: 1.25rem;
    color: var(--rt-dark);
  }
  p {
    margin: 0 0 var(--sp-4) 0;
    color: var(--rt-text);
    line-height: 1.55;
  }
  textarea {
    width: 100%;
    box-sizing: border-box;
    margin: 0 0 var(--sp-5) 0;
    padding: var(--sp-3);
    border: 1px solid var(--hairline);
    border-radius: var(--radius);
    font: inherit;
    color: inherit;
    resize: vertical;
  }
  .actions {
    display: flex;
    gap: var(--sp-3);
    justify-content: flex-end;
  }
</style>
