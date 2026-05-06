"""In-memory brute-force protection for the login endpoint.

Counts failed email lookups. After `threshold` invalid attempts, enters
throttled mode for `base_window` seconds.  Each additional batch of
`threshold` invalid attempts while throttled doubles the window duration.
Resets automatically once the throttle window expires with no new invalids.
"""

import time


class LoginThrottle:
    def __init__(self, threshold: int = 10, base_window: int = 3600) -> None:
        self.threshold = threshold
        self.base_window = base_window
        self.invalid_count = 0
        self.throttle_start: float | None = None
        self.escalation_level = 1

    @property
    def is_throttled(self) -> bool:
        if self.throttle_start is None:
            return False
        window = self.base_window * self.escalation_level
        if time.time() - self.throttle_start > window:
            self._reset()
            return False
        return True

    @property
    def current_window(self) -> int:
        """Current throttle window in seconds (for logging/diagnostics)."""
        return self.base_window * self.escalation_level

    def record_invalid(self) -> None:
        """Record an invalid email attempt and possibly trigger/escalate throttle."""
        self.invalid_count += 1
        if self.invalid_count >= self.threshold:
            if self.throttle_start is not None:
                self.escalation_level *= 2
            self.throttle_start = time.time()
            self.invalid_count = 0

    def _reset(self) -> None:
        self.invalid_count = 0
        self.throttle_start = None
        self.escalation_level = 1


login_throttle = LoginThrottle()
