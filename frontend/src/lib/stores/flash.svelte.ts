// Transient cross-route "flash" message for assignment warnings.
//
// Set on the /assign page right before navigating back to the calls list
// after "Done Assigning"; the calls list reads it reactively and shows a
// warning banner. The message clears itself after FLASH_TTL_MS so it reads
// as a heads-up, not a permanent fixture — the Send-Assignments
// confirmation is the durable safety net.

const FLASH_TTL_MS = 10_000;

let _message = $state("");
let _timer: ReturnType<typeof setTimeout> | null = null;

export const assignmentFlash = {
  get message() {
    return _message;
  },
};

function clearTimer() {
  if (_timer !== null) {
    clearTimeout(_timer);
    _timer = null;
  }
}

/**
 * Show `message` as the assignment flash, auto-clearing after the TTL. An
 * empty/whitespace message clears any current flash instead (no warning to
 * show ⇒ no banner).
 */
export function setAssignmentFlash(message: string): void {
  clearTimer();
  _message = message.trim();
  if (_message) {
    _timer = setTimeout(() => {
      _message = "";
      _timer = null;
    }, FLASH_TTL_MS);
  }
}

/** Clear the flash immediately (e.g. user-dismissed). */
export function dismissAssignmentFlash(): void {
  clearTimer();
  _message = "";
}
