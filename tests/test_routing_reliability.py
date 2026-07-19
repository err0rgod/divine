from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest

from divine_router.config.models import RetryPolicy
from divine_router.errors import DivineError, ProviderError
from divine_router.models.canonical import CanonicalRequest, CanonicalResponse
from divine_router.models.streaming import StreamEvent
from divine_router.reliability.circuit_breaker import CircuitBreaker, CircuitState
from divine_router.reliability.executor import FallbackExecutor, ProviderTarget
from divine_router.routing.models import ModelCapabilities, ModelRecord, ModelRegistry
from divine_router.routing.router import AutoRouter, RouteConstraints
from tests.conftest import FakeProvider


def test_capability_filtering_and_auto_scoring() -> None:
    registry = ModelRegistry()
    registry.register(ModelRecord("basic", "chat", ModelCapabilities(tools=False)))
    registry.register(
        ModelRecord(
            "capable",
            "agent",
            ModelCapabilities(tools=True, parallel_tools=True, reasoning=True),
        )
    )
    request = CanonicalRequest(
        model="auto",
        messages=[],
        tools=[{"name": "lookup", "parameters": {}}],
    )
    decision = AutoRouter(registry).auto(request, RouteConstraints())
    assert decision.selected.provider_id == "capable"


def test_constraints_can_eliminate_all_routes() -> None:
    registry = ModelRegistry()
    registry.register(ModelRecord("only", "model"))
    with pytest.raises(DivineError, match="no configured model"):
        AutoRouter(registry).auto(
            CanonicalRequest(model="auto", messages=[]),
            RouteConstraints(deny_providers=frozenset({"only"})),
        )


def test_circuit_breaker_opens() -> None:
    breaker = CircuitBreaker(failure_threshold=2)
    breaker.failure()
    assert breaker.failures == 1
    breaker.failure()
    assert breaker.state is CircuitState.OPEN
    assert not breaker.allow_request()


class FailingProvider(FakeProvider):
    provider_id = "failing"

    async def complete(self, request: CanonicalRequest, model: str) -> CanonicalResponse:
        raise ProviderError("down", status_code=503)


class FailingStreamProvider(FailingProvider):
    async def stream(self, request: CanonicalRequest, model: str) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(type="response.start", response_id="failed")
        raise ProviderError("stream unavailable", status_code=503)


class MidStreamFailingProvider(FailingProvider):
    async def stream(self, request: CanonicalRequest, model: str) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(type="response.start", response_id="partial")
        yield StreamEvent(type="content.delta", response_id="partial", delta="visible")
        raise ProviderError("stream broke", status_code=503, response_started=True)


class IdleStreamProvider(FailingProvider):
    async def stream(self, request: CanonicalRequest, model: str) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(type="response.start", response_id="idle")
        await asyncio.sleep(1)
        yield StreamEvent(type="response.complete", response_id="idle")


@pytest.mark.asyncio
async def test_fallback_executor_selects_second_provider() -> None:
    first = FailingProvider()
    second = FakeProvider()
    executor = FallbackExecutor(deadline_seconds=2)
    result = await executor.execute(
        CanonicalRequest(model="demo", messages=[]),
        [
            ProviderTarget(first, "bad", RetryPolicy(max_attempts=1)),
            ProviderTarget(second, "good", RetryPolicy(max_attempts=1)),
        ],
    )
    assert result.provider_id == "mock"
    assert result.model == "good"
    assert result.fallback_count == 1


@pytest.mark.asyncio
async def test_stream_fallback_occurs_only_before_visible_output() -> None:
    second = FakeProvider()
    executor = FallbackExecutor(deadline_seconds=2)
    result = await executor.prepare_stream(
        CanonicalRequest(model="demo", messages=[], stream=True),
        [
            ProviderTarget(FailingStreamProvider(), "bad", RetryPolicy(max_attempts=1)),
            ProviderTarget(second, "good", RetryPolicy(max_attempts=1)),
        ],
        idle_timeout_seconds=1,
    )
    events = [event async for event in result.events]
    assert result.provider_id == "mock"
    assert result.fallback_count == 1
    assert any(event.delta == "DIVINE_" for event in events)

    unused_fallback = FakeProvider()
    committed = await executor.prepare_stream(
        CanonicalRequest(model="demo", messages=[], stream=True),
        [
            ProviderTarget(MidStreamFailingProvider(), "bad", RetryPolicy(max_attempts=1)),
            ProviderTarget(unused_fallback, "good", RetryPolicy(max_attempts=1)),
        ],
        idle_timeout_seconds=1,
    )
    with pytest.raises(ProviderError, match="stream broke"):
        _ = [event async for event in committed.events]
    assert committed.provider_id == "failing"
    assert unused_fallback.requests == []


@pytest.mark.asyncio
async def test_stream_idle_timeout_can_fallback_before_output() -> None:
    executor = FallbackExecutor(deadline_seconds=2)
    result = await executor.prepare_stream(
        CanonicalRequest(model="demo", messages=[], stream=True),
        [
            ProviderTarget(IdleStreamProvider(), "idle", RetryPolicy(max_attempts=1)),
            ProviderTarget(FakeProvider(), "good", RetryPolicy(max_attempts=1)),
        ],
        idle_timeout_seconds=0.01,
    )
    assert result.provider_id == "mock"
    assert result.fallback_count == 1
