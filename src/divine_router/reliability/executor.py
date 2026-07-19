"""Provider retry/fallback execution with total deadlines."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

from divine_router.config.models import RetryPolicy
from divine_router.errors import ProviderError
from divine_router.models.canonical import CanonicalRequest, CanonicalResponse
from divine_router.providers.base import Provider
from divine_router.reliability.circuit_breaker import CircuitBreaker
from divine_router.reliability.retry import backoff, retryable


@dataclass(frozen=True, slots=True)
class ProviderTarget:
    provider: Provider
    model: str
    retry: RetryPolicy


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    response: CanonicalResponse
    provider_id: str
    model: str
    fallback_count: int


class FallbackExecutor:
    def __init__(self, deadline_seconds: float = 120) -> None:
        self.deadline_seconds = deadline_seconds
        self.breakers: dict[str, CircuitBreaker] = {}

    async def execute(
        self, request: CanonicalRequest, targets: Sequence[ProviderTarget]
    ) -> ExecutionResult:
        if not targets:
            raise ProviderError("no provider targets are available", status_code=503)
        async with asyncio.timeout(self.deadline_seconds):
            last_error: ProviderError | None = None
            fallback_count = 0
            for target in targets:
                breaker = self.breakers.setdefault(target.provider.provider_id, CircuitBreaker())
                if not breaker.allow_request():
                    fallback_count += 1
                    continue
                for attempt in range(target.retry.max_attempts):
                    try:
                        response = await target.provider.complete(request, target.model)
                    except ProviderError as exc:
                        last_error = exc
                        breaker.failure()
                        if not retryable(exc) or attempt + 1 >= target.retry.max_attempts:
                            break
                        await asyncio.sleep(
                            backoff(
                                attempt,
                                target.retry.base_delay_seconds,
                                target.retry.max_delay_seconds,
                                exc.retry_after,
                            )
                        )
                    else:
                        breaker.success()
                        return ExecutionResult(
                            response=response,
                            provider_id=target.provider.provider_id,
                            model=target.model,
                            fallback_count=fallback_count,
                        )
                fallback_count += 1
            raise last_error or ProviderError("all providers are unavailable", status_code=503)
