"""Native Anthropic Messages provider adapter."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import httpx

from divine_router.config.models import ProviderConfig
from divine_router.errors import ProviderError
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
from divine_router.providers.base import Provider, ProviderHealth
from divine_router.providers.http import authentication, provider_error


class AnthropicProvider(Provider):
    def __init__(
        self,
        config: ProviderConfig,
        credential: str | None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config
        self.provider_id = config.id
        self.health = ProviderHealth(config.id)
        headers, self.params = authentication(config, credential)
        headers.setdefault("anthropic-version", "2023-06-01")
        self.client = client or httpx.AsyncClient(
            base_url=config.base_url,
            headers=headers,
            timeout=httpx.Timeout(config.timeout_seconds),
        )

    @staticmethod
    def request_payload(request: CanonicalRequest, model: str) -> dict[str, Any]:
        system = "\n".join(
            part.text or ""
            for message in request.messages
            if message.role in {"system", "developer"}
            for part in message.content
            if part.kind is ContentKind.TEXT
        )
        messages = [
            AnthropicProvider._message(message)
            for message in request.messages
            if message.role not in {"system", "developer"}
        ]
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_output_tokens or 1024,
            "stream": request.stream,
        }
        if system:
            payload["system"] = system
        for key, value in {
            "temperature": request.temperature,
            "top_p": request.top_p,
            "top_k": request.top_k,
        }.items():
            if value is not None:
                payload[key] = value
        if request.stop:
            payload["stop_sequences"] = request.stop
        if request.tools:
            payload["tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters,
                }
                for tool in request.tools
            ]
        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice
        return payload

    @staticmethod
    def _message(message: CanonicalMessage) -> dict[str, Any]:
        role = "assistant" if message.role == "assistant" else "user"
        blocks: list[dict[str, Any]] = []
        for part in message.content:
            if part.kind is ContentKind.TEXT:
                blocks.append({"type": "text", "text": part.text})
            elif part.kind is ContentKind.IMAGE:
                if part.data is not None:
                    blocks.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": part.media_type,
                                "data": part.data,
                            },
                        }
                    )
                elif part.image_url:
                    blocks.append(
                        {"type": "image", "source": {"type": "url", "url": part.image_url}}
                    )
            elif part.kind is ContentKind.TOOL_RESULT:
                blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": part.tool_call_id,
                        "content": part.text if part.text is not None else part.data,
                    }
                )
        blocks.extend(
            {
                "type": "tool_use",
                "id": call.id,
                "name": call.name,
                "input": json.loads(call.arguments),
            }
            for call in message.tool_calls
        )
        return {"role": role, "content": blocks}

    async def complete(self, request: CanonicalRequest, model: str) -> CanonicalResponse:
        response = await self.client.post(
            "messages", json=self.request_payload(request, model), params=self.params
        )
        if response.is_error:
            raise provider_error(response)
        try:
            payload = response.json()
            contents: list[CanonicalContent] = []
            calls: list[CanonicalToolCall] = []
            for block in payload["content"]:
                if block["type"] == "text":
                    contents.append(CanonicalContent(kind=ContentKind.TEXT, text=block["text"]))
                elif block["type"] == "tool_use":
                    calls.append(
                        CanonicalToolCall(
                            id=block["id"],
                            name=block["name"],
                            arguments=json.dumps(block["input"], separators=(",", ":")),
                        )
                    )
            usage = payload.get("usage", {})
            result = CanonicalResponse(
                id=payload.get("id", f"msg_{uuid4().hex}"),
                model=payload.get("model", model),
                message=CanonicalMessage(role="assistant", content=contents, tool_calls=calls),
                finish_reason=payload.get("stop_reason"),
                usage=TokenUsage(
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                    cached_input_tokens=usage.get("cache_read_input_tokens", 0),
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError("provider returned a malformed Anthropic message") from exc
        self.health.success()
        return result

    async def stream(self, request: CanonicalRequest, model: str) -> AsyncIterator[StreamEvent]:
        response_id = f"msg_{uuid4().hex}"
        emitted = False
        yield StreamEvent(type="response.start", response_id=response_id)
        try:
            async with self.client.stream(
                "POST",
                "messages",
                json=self.request_payload(request.model_copy(update={"stream": True}), model),
                params=self.params,
            ) as response:
                if response.is_error:
                    await response.aread()
                    raise provider_error(response)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    payload = json.loads(line[5:].strip())
                    if payload.get("type") == "content_block_delta":
                        delta = payload.get("delta", {})
                        if delta.get("type") == "text_delta":
                            emitted = True
                            yield StreamEvent(
                                type="content.delta",
                                response_id=response_id,
                                delta=delta.get("text", ""),
                            )
                        elif delta.get("type") == "input_json_delta":
                            yield StreamEvent(
                                type="tool_call.delta",
                                response_id=response_id,
                                index=payload.get("index", 0),
                                item={"arguments": delta.get("partial_json", "")},
                            )
            self.health.success()
            yield StreamEvent(type="response.complete", response_id=response_id)
        except (httpx.HTTPError, json.JSONDecodeError, ProviderError) as exc:
            self.health.failure(type(exc).__name__)
            if isinstance(exc, ProviderError):
                exc.response_started = emitted
                raise
            raise ProviderError("provider stream failed", response_started=emitted) from exc

    async def discover_models(self) -> list[str]:
        if not self.config.model_discovery_path:
            return list(self.config.models)
        response = await self.client.get(
            self.config.model_discovery_path.lstrip("/"), params=self.params
        )
        if response.is_error:
            raise provider_error(response)
        return [str(item["id"]) for item in response.json().get("data", []) if item.get("id")]
