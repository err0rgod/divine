from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from divine_router.errors import CompatibilityError, DivineError, ProviderError
from divine_router.models.canonical import (
    CanonicalContent,
    CanonicalMessage,
    CanonicalRequest,
    CanonicalResponse,
    CanonicalToolCall,
    ContentKind,
    TokenUsage,
)
from divine_router.protocols.anthropic_messages import (
    AnthropicMessagesRequest,
)
from divine_router.protocols.anthropic_messages import (
    serialize_response as serialize_anthropic,
)
from divine_router.protocols.openai_chat import (
    ChatCompletionRequest,
)
from divine_router.protocols.openai_chat import (
    serialize_response as serialize_chat,
)
from divine_router.protocols.responses import (
    ResponsesRequest,
)
from divine_router.protocols.responses import (
    serialize_response as serialize_responses,
)
from divine_router.reliability.circuit_breaker import CircuitBreaker, CircuitState
from divine_router.reliability.executor import FallbackExecutor
from divine_router.reliability.retry import backoff, retryable
from divine_router.routing.classifier import TaskClass, classify
from divine_router.routing.models import (
    DiscoveryEntry,
    ModelCapabilities,
    ModelRecord,
    ModelRegistry,
)
from divine_router.routing.router import AutoRouter, RouteConstraints


def response_with_tool(reason: str = "tool_calls") -> CanonicalResponse:
    return CanonicalResponse(
        id="chatcmpl-edge",
        model="mock/demo",
        message=CanonicalMessage(
            role="assistant",
            tool_calls=[CanonicalToolCall(id="call_1", name="lookup", arguments='{"x":1}')],
        ),
        finish_reason=reason,
        usage=TokenUsage(input_tokens=1, output_tokens=2),
    )


def test_chat_validation_and_tool_serialization_edges() -> None:
    with pytest.raises(ValidationError, match="mutually exclusive"):
        ChatCompletionRequest(model="x", messages=[], max_tokens=1, max_completion_tokens=2)
    with pytest.raises(CompatibilityError, match="role"):
        ChatCompletionRequest(model="x", messages=[{"role": "alien"}]).to_canonical()
    with pytest.raises(CompatibilityError, match="objects"):
        ChatCompletionRequest(
            model="x", messages=[{"role": "user", "content": ["bad"]}]
        ).to_canonical()
    with pytest.raises(CompatibilityError, match="tool_call_id"):
        ChatCompletionRequest(
            model="x", messages=[{"role": "tool", "content": "result"}]
        ).to_canonical()
    with pytest.raises(CompatibilityError, match="function tools"):
        ChatCompletionRequest(model="x", messages=[], tools=[{"type": "computer"}]).to_canonical()
    serialized = serialize_chat(response_with_tool())
    assert serialized["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "lookup"


def test_responses_content_reasoning_and_serialization_edges() -> None:
    request = ResponsesRequest(
        model="mock/demo",
        input=[
            {"type": "message", "role": "user", "content": "hello"},
            {"type": "reasoning", "summary": [{"type": "summary_text", "text": "summary"}]},
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_image", "file_id": "file_1"}],
            },
        ],
    )
    canonical = request.to_canonical()
    assert canonical.messages[1].content[0].text == "summary"
    assert canonical.messages[2].content[0].kind is ContentKind.IMAGE
    serialized = serialize_responses(response_with_tool(), request)
    assert serialized["output"][0]["type"] == "function_call"
    with pytest.raises(CompatibilityError, match="item type"):
        ResponsesRequest(model="x", input=[{"type": "file_search_call"}]).to_canonical()
    with pytest.raises(CompatibilityError, match="content type"):
        ResponsesRequest(
            model="x",
            input=[{"type": "message", "role": "user", "content": [{"type": "input_file"}]}],
        ).to_canonical()


def test_anthropic_system_images_errors_and_serialization() -> None:
    body = AnthropicMessagesRequest(
        model="mock/demo",
        max_tokens=5,
        system=[{"type": "text", "text": "system"}],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": "abc"},
                    },
                    {"type": "image", "source": {"type": "url", "url": "https://example.test/i"}},
                ],
            }
        ],
    )
    canonical = body.to_canonical()
    assert canonical.messages[0].role == "system"
    assert len(canonical.messages[1].content) == 2
    with pytest.raises(CompatibilityError, match="image source"):
        AnthropicMessagesRequest(
            model="x",
            max_tokens=1,
            messages=[{"role": "user", "content": [{"type": "image", "source": {"type": "file"}}]}],
        ).to_canonical()
    with pytest.raises(CompatibilityError, match="content block"):
        AnthropicMessagesRequest(
            model="x",
            max_tokens=1,
            messages=[{"role": "user", "content": [{"type": "document"}]}],
        ).to_canonical()
    serialized = serialize_anthropic(response_with_tool())
    assert serialized["content"][0]["input"] == {"x": 1}
    assert serialized["stop_reason"] == "tool_use"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("please debug this traceback", TaskClass.DEBUGGING),
        ("summarize this document", TaskClass.SUMMARIZATION),
        ("write a poem", TaskClass.CREATIVE_WRITING),
        ("hello there", TaskClass.SIMPLE_CHAT),
    ],
)
def test_classifier_classes(text: str, expected: TaskClass) -> None:
    request = CanonicalRequest(
        model="auto",
        messages=[
            CanonicalMessage(
                role="user", content=[CanonicalContent(kind=ContentKind.TEXT, text=text)]
            )
        ],
    )
    assert classify(request) is expected


def test_model_registry_cache_and_alias_errors() -> None:
    registry = ModelRegistry(ttl_seconds=10)
    model = ModelRecord("p", "m")
    registry.cache_discovery("p", [model])
    assert registry.discovered("p") == [model]
    registry._discovery["p"] = DiscoveryEntry([model], datetime.now(UTC) - timedelta(seconds=1))
    assert registry.discovered("p") is None
    with pytest.raises(DivineError, match="unknown model"):
        registry.get("missing/model")
    with pytest.raises(DivineError, match="no candidates"):
        AutoRouter(registry).explicit("empty", {"empty": []})


def test_router_filters_output_structured_vision_cost_and_health() -> None:
    registry = ModelRegistry()
    registry.register(
        ModelRecord(
            "p",
            "capable",
            ModelCapabilities(
                streaming=True,
                structured_output=True,
                vision=True,
                max_output_tokens=100,
                reasoning=True,
            ),
            input_cost_per_million=1,
            output_cost_per_million=1,
            typical_latency_ms=10,
        )
    )
    request = CanonicalRequest(
        model="auto",
        messages=[
            CanonicalMessage(
                role="user",
                content=[
                    CanonicalContent(kind=ContentKind.IMAGE, image_url="https://example.test/i")
                ],
            )
        ],
        stream=True,
        max_output_tokens=50,
        response_format={"type": "json_schema"},
    )
    decision = AutoRouter(registry).auto(request, RouteConstraints(max_cost=3, prefer="quality"))
    assert decision.selected.model_id == "capable"
    with pytest.raises(DivineError, match="no configured model"):
        AutoRouter(registry).auto(request, RouteConstraints(max_cost=1))


def test_retry_and_circuit_recovery_edges() -> None:
    retry_error = ProviderError("busy", status_code=429, category="rate_limit_error")
    auth_error = ProviderError("bad key", status_code=401, category="provider_authentication_error")
    assert retryable(retry_error)
    assert not retryable(auth_error)
    assert backoff(2, 0.1, 1, retry_after=3) == 1
    assert 0 <= backoff(1, 0.1, 1) <= 0.2
    breaker = CircuitBreaker(failure_threshold=1, recovery_seconds=0)
    breaker.failure()
    assert breaker.allow_request()
    assert breaker.state is CircuitState.HALF_OPEN
    breaker.success()
    assert breaker.failures == 0


@pytest.mark.asyncio
async def test_executor_rejects_empty_targets() -> None:
    with pytest.raises(ProviderError, match="no provider targets"):
        await FallbackExecutor().execute(CanonicalRequest(model="x", messages=[]), [])
