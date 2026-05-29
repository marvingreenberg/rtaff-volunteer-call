<script lang="ts">
  // Renders the active confirm request from $lib/stores/confirm. Place
  // exactly once at the top of +layout.svelte. Callsites use the
  // confirmDialog() helper; this component is the singleton view.
  //
  // Uses the native <dialog> element with .showModal() so the browser
  // gives us focus trapping, Esc-to-close, and an inert backdrop for
  // free. CSS styles the surface and the ::backdrop pseudo-element.
  import { confirmState, resolveConfirm } from "$lib/stores/confirm.svelte";

  let dialogEl: HTMLDialogElement | null = $state(null);
  let okButton: HTMLButtonElement | null = $state(null);
  let cancelButton: HTMLButtonElement | null = $state(null);

  // Open/close as the store flips. $effect runs after the DOM updates so
  // dialogEl and the buttons are in place.
  $effect(() => {
    const pending = confirmState.pending;
    if (!dialogEl) return;
    if (pending) {
      // jsdom doesn't implement HTMLDialogElement.showModal / .close /
      // .open, so guard the calls. In jsdom the test still sees the
      // rendered DOM; the test environment doesn't need real modal
      // semantics.
      if (typeof dialogEl.showModal === "function" && !dialogEl.open) {
        dialogEl.showModal();
      }
      // Focus the safer choice: Cancel for danger actions, OK for the
      // rest. Wait one microtask so the just-rendered DOM is hookable.
      queueMicrotask(() => {
        const target = pending.danger ? cancelButton : okButton;
        target?.focus();
      });
    } else if (typeof dialogEl.close === "function" && dialogEl.open) {
      dialogEl.close();
    }
  });

  function onClose() {
    // The dialog's built-in close event fires for Esc, backdrop close,
    // form method=dialog submit, or explicit .close(). If the store
    // still has a pending request, treat it as a cancel — covers the Esc
    // case where the user didn't click either button.
    if (confirmState.pending) resolveConfirm(false);
  }

  function onBackdropClick(e: MouseEvent) {
    // Click on the dialog element itself (not its inner content) is the
    // backdrop. Treating that as cancel matches OS conventions.
    if (e.target === dialogEl) resolveConfirm(false);
  }
</script>

{#if confirmState.pending}
  {@const p = confirmState.pending}
  <dialog
    bind:this={dialogEl}
    onclose={onClose}
    onclick={onBackdropClick}
    role={p.danger ? "alertdialog" : "dialog"}
    aria-labelledby="confirm-title"
    aria-describedby="confirm-body"
    class:danger={p.danger}
  >
    <div class="surface">
      <h2 id="confirm-title">{p.title}</h2>
      <p id="confirm-body">{p.body}</p>
      <div class="actions">
        <button
          type="button"
          class="btn btn-secondary"
          bind:this={cancelButton}
          onclick={() => resolveConfirm(false)}
        >
          {p.cancelLabel ?? "Cancel"}
        </button>
        <button
          type="button"
          class={p.danger ? "btn btn-danger" : "btn btn-primary"}
          bind:this={okButton}
          onclick={() => resolveConfirm(true)}
        >
          {p.okLabel ?? "OK"}
        </button>
      </div>
    </div>
  </dialog>
{/if}

<style>
  /* Reset the native dialog chrome; let .surface inside own the look. */
  dialog {
    padding: 0;
    border: 0;
    background: transparent;
    color: inherit;
    max-width: min(420px, calc(100vw - var(--sp-5) * 2));
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
    margin: 0 0 var(--sp-5) 0;
    color: var(--rt-text);
    line-height: 1.55;
  }
  .actions {
    display: flex;
    gap: var(--sp-3);
    justify-content: flex-end;
  }
</style>
