from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest

from divine_router.config.models import (
    AdapterFamily,
    DivineConfig,
    ProviderConfig,
    VerificationStatus,
)
from divine_router.models.canonical import (
    CanonicalContent,
    CanonicalMessage,
    CanonicalRequest,
    CanonicalResponse,
    CanonicalToolCall,
    ContentKind,
    TokenUsage,
)
from divine_router.models.streaming import StreamEvent
from divine_router.persistence.database import Database
from divine_router.providers.base import Provider, ProviderHealth
from divine_router.routing.models import ModelCapabilities, ModelRecord, ModelRegistry
from divine_router.service import Gateway


class FakeProvider(Provider):
    provider_id = "mock"

    def __init__(self) -> None:
        self.health = ProviderHealth(self.provider_id)
        self.requests: list[CanonicalRequest] = []

    async def complete(self, request: CanonicalRequest, model: str) -> CanonicalResponse:
        self.requests.append(request)
        tool_calls = (
            [CanonicalToolCall(id="call_1", name=request.tools[0].name, arguments='{"value":1}')]
            if request.tools
            else []
        )
        return CanonicalResponse(
            id="chatcmpl-test",
            model=model,
            message=CanonicalMessage(
                role="assistant",
                content=(
                    []
                    if tool_calls
                    else [CanonicalContent(kind=ContentKind.TEXT, text="DIVINE_OK")]
                ),
                tool_calls=tool_calls,
            ),
            finish_reason="tool_calls" if tool_calls else "stop",
            usage=TokenUsage(input_tokens=3, output_tokens=2),
        )

    async def stream(self, request: CanonicalRequest, model: str) -> AsyncIterator[StreamEvent]:
        self.requests.append(request)
        yield StreamEvent(type="response.start", response_id="chatcmpl-stream")
        if request.tools:
            yield StreamEvent(
                type="tool_call.start",
                response_id="chatcmpl-stream",
                item={
                    "id": "call_stream_1",
                    "name": request.tools[0].name,
                    "arguments": '{"value":',
                },
            )
            yield StreamEvent(
                type="tool_call.delta",
                response_id="chatcmpl-stream",
                item={"arguments": "1}"},
            )
            yield StreamEvent(
                type="response.complete",
                response_id="chatcmpl-stream",
                usage={"input_tokens": 3, "output_tokens": 2},
            )
            return
        yield StreamEvent(type="content.delta", response_id="chatcmpl-stream", delta="DIVINE_")
        yield StreamEvent(type="content.delta", response_id="chatcmpl-stream", delta="OK")
        yield StreamEvent(
            type="response.complete",
            response_id="chatcmpl-stream",
            usage={"input_tokens": 3, "output_tokens": 2},
        )

    async def discover_models(self) -> list[str]:
        return ["demo"]


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def gateway(fake_provider: FakeProvider) -> Gateway:
    provider_config = ProviderConfig(
        id="mock",
        display_name="Mock",
        adapter=AdapterFamily.OPENAI,
        base_url="http://127.0.0.1:9999/v1",
        enabled=True,
        models=["demo"],
        capabilities={
            "responses": True,
            "tools": True,
            "parallel_tools": True,
            "structured_output": True,
            "vision": True,
            "reasoning": True,
        },
        verification=VerificationStatus.VERIFIED_MOCKED,
    )
    config = DivineConfig(
        providers=[provider_config],
        aliases={"default": ["mock/demo"], "auto": ["mock/demo"]},
    )
    registry = ModelRegistry()
    registry.register(
        ModelRecord(
            "mock",
            "demo",
            ModelCapabilities(
                responses=True,
                tools=True,
                parallel_tools=True,
                structured_output=True,
                vision=True,
                reasoning=True,
            ),
        )
    )
    return Gateway(config, {"mock": fake_provider}, registry)


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "divine.db")
    try:
        yield database
    finally:
        database.close()
