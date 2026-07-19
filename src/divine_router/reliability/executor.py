"""Provider retry/fallback execution with total deadlines."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass

from divine_router.config.models import RetryPolicy
from divine_router.errors import ProviderError
from divine_router.models.canonical import CanonicalRequest, CanonicalResponse
from divine_router.models.streaming import StreamEvent
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


@dataclass(frozen=True, slots=True)
class StreamExecutionResult:
    events: AsyncIterator[StreamEvent]
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

    async def prepare_stream(
        self,
        request: CanonicalRequest,
        targets: Sequence[ProviderTarget],
        idle_timeout_seconds: float,
    ) -> StreamExecutionResult:
        """Select a stream with retries/fallbacks only before client-visible output."""
        if not targets:
            raise ProviderError("no provider targets are available", status_code=503)
        deadline = asyncio.get_running_loop().time() + self.deadline_seconds
        last_error: ProviderError | None = None
        fallback_count = 0
        for target in targets:
            breaker = self.breakers.setdefault(target.provider.provider_id, CircuitBreaker())
            if not breaker.allow_request():
                fallback_count += 1
                continue
            for attempt in range(target.retry.max_attempts):
                iterator = target.provider.stream(request, target.model).__aiter__()
                buffered: list[StreamEvent] = []
                attempt_error: ProviderError | None = None
                try:
                    while True:
                        event = await _next_stream_event(iterator, idle_timeout_seconds, deadline)
                        buffered.append(event)
                        if event.type in {
                            "content.delta",
                            "tool_call.start",
                            "tool_call.delta",
                            "response.complete",
                        }:
                            breaker.success()
                            return StreamExecutionResult(
                                _committed_stream(
                                    buffered,
                                    iterator,
                                    idle_timeout_seconds,
                                    deadline,
                                    breaker,
                                ),
                                target.provider.provider_id,
                                target.model,
                                fallback_count,
                            )
                except StopAsyncIteration:
                    attempt_error = ProviderError(
                        "provider stream ended without a completion event", status_code=502
                    )
                except ProviderError as exc:
                    attempt_error = exc
                finally:
                    if attempt_error is not None:
                        await _close_iterator(iterator)
                assert attempt_error is not None
                last_error = attempt_error
                breaker.failure()
                if not retryable(last_error) or attempt + 1 >= target.retry.max_attempts:
                    break
                await asyncio.sleep(
                    backoff(
                        attempt,
                        target.retry.base_delay_seconds,
                        target.retry.max_delay_seconds,
                        last_error.retry_after,
                    )
                )
            fallback_count += 1
        raise last_error or ProviderError("all providers are unavailable", status_code=503)


async def _next_stream_event(
    iterator: AsyncIterator[StreamEvent], idle_timeout_seconds: float, deadline: float
) -> StreamEvent:
    remaining = deadline - asyncio.get_running_loop().time()
    if remaining <= 0:
        raise ProviderError("total request deadline exceeded", status_code=504)
    timeout = min(idle_timeout_seconds, remaining)
    try:
        return await asyncio.wait_for(anext(iterator), timeout=timeout)
    except TimeoutError as exc:
        message = (
            "streaming idle timeout exceeded"
            if timeout == idle_timeout_seconds
            else ("total request deadline exceeded")
        )
        raise ProviderError(message, status_code=504) from exc


async def _committed_stream(
    buffered: list[StreamEvent],
    iterator: AsyncIterator[StreamEvent],
    idle_timeout_seconds: float,
    deadline: float,
    breaker: CircuitBreaker,
) -> AsyncIterator[StreamEvent]:
    try:
        for event in buffered:
            yield event
        while True:
            try:
                event = await _next_stream_event(iterator, idle_timeout_seconds, deadline)
            except StopAsyncIteration:
                return
            yield event
            if event.type == "response.complete":
                breaker.success()
                return
    except ProviderError:
        breaker.failure()
        raise
    finally:
        await _close_iterator(iterator)


async def _close_iterator(iterator: AsyncIterator[StreamEvent]) -> None:
    close = getattr(iterator, "aclose", None)
    if close is not None:
        await close()
