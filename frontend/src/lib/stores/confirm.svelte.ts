// In-app confirmation dialog backing store.
//
// Replaces `window.confirm()` callsites. Callsites import `confirmDialog()`
// and await its boolean result; a single `<ConfirmDialogHost>` instance
// (mounted in +layout.svelte) renders the active dialog.
//
// Why not native confirm: Playwright's default dialog handler auto-dismisses
// native confirms, which breaks both `make demo` and any session where
// Claude-in-Chrome (a Playwright-backed extension) is attached. A DOM-based
// dialog is just regular markup; automation tools drive it with normal
// selectors. The component also matches the soft-modular aesthetic and gives
// us controllable keyboard + focus behavior.

export interface ConfirmRequest {
  title: string;
  body: string;
  okLabel?: string;
  cancelLabel?: string;
  // Visual variant for destructive actions. The OK button picks up
  // .btn-danger styling and the dialog uses role=alertdialog.
  danger?: boolean;
}

interface PendingConfirm extends ConfirmRequest {
  resolve: (accepted: boolean) => void;
}

let _pending = $state<PendingConfirm | null>(null);

export const confirmState = {
  get pending() {
    return _pending;
  },
};

export function confirmDialog(req: ConfirmRequest): Promise<boolean> {
  // If a prior dialog is still open, resolving it as cancelled keeps the
  // promise chain clean. The new request takes over.
  if (_pending) {
    _pending.resolve(false);
  }
  return new Promise<boolean>((resolve) => {
    _pending = { ...req, resolve };
  });
}

// Called by ConfirmDialogHost when the user picks an answer.
export function resolveConfirm(accepted: boolean): void {
  const p = _pending;
  if (!p) return;
  _pending = null;
  p.resolve(accepted);
}
