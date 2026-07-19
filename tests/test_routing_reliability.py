from __future__ import annotations

import pytest

from divine_router.config.models import RetryPolicy
from divine_router.errors import DivineError, ProviderError
from divine_router.models.canonical import CanonicalRequest, CanonicalResponse
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
