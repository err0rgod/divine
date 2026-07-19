"""Configurable in-memory local rate limiter."""

from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic

from divine_router.errors import DivineError


class RateLimiter:
    def __init__(self, requests_per_minute: int) -> None:
        self.limit = requests_per_minute
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def check(self, client: str) -> None:
        now = monotonic()
        window = self._requests[client]
        while window and window[0] <= now - 60:
            window.popleft()
        if len(window) >= self.limit:
            raise DivineError(
                "Divine Router rate limit exceeded", "rate_limit_error", 429, "rate_limit_exceeded"
            )
        window.append(now)
