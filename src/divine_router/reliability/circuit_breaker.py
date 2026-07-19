"""Small provider-local circuit breaker state machine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from time import monotonic


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"


@dataclass(slots=True)
class CircuitBreaker:
    failure_threshold: int = 3
    recovery_seconds: float = 30
    state: CircuitState = CircuitState.CLOSED
    failures: int = 0
    opened_at: float | None = None

    def allow_request(self) -> bool:
        if self.state is CircuitState.CLOSED:
            return True
        if self.state is CircuitState.OPEN and self.opened_at is not None:
            if monotonic() - self.opened_at >= self.recovery_seconds:
                self.state = CircuitState.HALF_OPEN
                return True
        return self.state is CircuitState.HALF_OPEN

    def success(self) -> None:
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.opened_at = None

    def failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold or self.state is CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.opened_at = monotonic()
