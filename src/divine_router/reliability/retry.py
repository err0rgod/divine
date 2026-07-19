"""Retry classification and exponential backoff with jitter."""

from __future__ import annotations

import random

from divine_router.errors import ProviderError


def retryable(error: ProviderError) -> bool:
    return error.category in {"rate_limit_error", "provider_error"} and error.status_code in {
        408,
        409,
        425,
        429,
        500,
        502,
        503,
        504,
    }


def backoff(attempt: int, base: float, maximum: float, retry_after: float | None = None) -> float:
    if retry_after is not None:
        return min(maximum, retry_after)
    ceiling = min(maximum, base * (2**attempt))
    return random.uniform(0, ceiling)  # noqa: S311
