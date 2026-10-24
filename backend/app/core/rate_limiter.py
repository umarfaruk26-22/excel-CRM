import time
from collections import defaultdict
from typing import Dict, List, Tuple

class SimpleRateLimiter:
    """In-memory rate limiter to protect authentication endpoints from brute force."""
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        # key -> list of timestamp attempts
        self._attempts: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> Tuple[bool, int]:
        """
        Returns (is_allowed, remaining_seconds).
        If allowed, returns (True, 0).
        If locked, returns (False, retry_after_seconds).
        """
        now = time.time()
        # Clean older than window
        self._attempts[key] = [t for t in self._attempts[key] if now - t < self.window_seconds]

        if len(self._attempts[key]) >= self.max_attempts:
            oldest = self._attempts[key][0]
            remaining = int(self.window_seconds - (now - oldest))
            return False, max(remaining, 1)

        return True, 0

    def record_attempt(self, key: str):
        """Records a failed attempt timestamp."""
        self._attempts[key].append(time.time())

    def reset(self, key: str):
        """Resets attempts on successful authentication."""
        if key in self._attempts:
            del self._attempts[key]

login_limiter = SimpleRateLimiter(max_attempts=5, window_seconds=300)
