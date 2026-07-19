from __future__ import annotations

import json

import httpx
import pytest

from divine_router.config.models import AdapterFamily, ProviderConfig
from divine_router.models.canonical import (
    CanonicalContent,
    CanonicalMessage,
    CanonicalRequest,
    CanonicalTool,
    ContentKind,
)
from divine_router.providers.anthropic import AnthropicProvider
from divine_router.providers.http import authentication
from divine_router.providers.openai_compatible import OpenAICompatibleProvider


def canonical_request(stream: bool = False) -> CanonicalRequest:
    return CanonicalRequest(
        model="provider/demo",
        messages=[
            CanonicalMessage(
                role="user", content=[CanonicalContent(kind=ContentKind.TEXT, text="hello")]
            )
        ],
        stream=stream,
        max_output_tokens=12,
        tools=[CanonicalTool(name="lookup", parameters={"type": "object"})],
    )


def config(adapter: AdapterFamily = AdapterFamily.OPENAI) -> ProviderConfig:
    return ProviderConfig(
        id="provider",
        display_name="Provider",
        adapter=adapter,
        base_url="https://provider.test/v1",
        enabled=True,
    )


def test_provider_authentication_styles() -> None:
    bearer, _ = authentication(config(), "secret")
    assert bearer["Authorization"] == "Bearer secret"
    google = config().model_copy(update={"auth_style": "x-goog-api-key"})
    headers, _ = authentication(google, "secret")
    assert headers["x-goog-api-key"] == "secret"


@pytest.mark.asyncio
async def test_openai_provider_non_stream_and_payload() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://provider.test/v1/chat/completions"
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-1",
                "model": "demo",
                "choices": [
                    {"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1},
            },
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://provider.test/v1"
    ) as client:
        provider = OpenAICompatibleProvider(config(), None, client)
        response = await provider.complete(canonical_request(), "demo")
    assert captured["max_completion_tokens"] == 12
    assert captured["tools"]
    assert response.message.content[0].text == "ok"
    assert response.usage.total_tokens == 3


@pytest.mark.asyncio
async def test_openai_provider_stream() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        data = (
            'data: {"choices":[{"delta":{"content":"one"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"two"}}]}\n\n'
            "data: [DONE]\n\n"
        )
        return httpx.Response(200, text=data, headers={"content-type": "text/event-stream"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://provider.test/v1"
    ) as client:
        provider = OpenAICompatibleProvider(config(), None, client)
        events = [item async for item in provider.stream(canonical_request(True), "demo")]
    assert [item.delta for item in events if item.type == "content.delta"] == ["one", "two"]


@pytest.mark.asyncio
async def test_anthropic_provider_translation() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "msg_1",
                "model": "demo",
                "content": [{"type": "text", "text": "ok"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 2, "output_tokens": 1},
            },
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://provider.test/v1"
    ) as client:
        provider = AnthropicProvider(config(AdapterFamily.ANTHROPIC), None, client)
        response = await provider.complete(canonical_request(), "demo")
    assert captured["max_tokens"] == 12
    assert response.id == "msg_1"
