"""Generic adapter shared by OpenAI-compatible providers and gateways."""

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


class OpenAICompatibleProvider(Provider):
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
        self.client = client or httpx.AsyncClient(
            base_url=config.base_url,
            headers=headers,
            timeout=httpx.Timeout(config.timeout_seconds),
        )

    @staticmethod
    def request_payload(request: CanonicalRequest, model: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                OpenAICompatibleProvider._message(message) for message in request.messages
            ],
            "stream": request.stream,
        }
        optional = {
            "temperature": request.temperature,
            "top_p": request.top_p,
            "max_completion_tokens": request.max_output_tokens,
            "seed": request.seed,
            "response_format": request.response_format,
            "tool_choice": request.tool_choice,
        }
        payload.update({key: value for key, value in optional.items() if value is not None})
        if request.stop:
            payload["stop"] = request.stop
        if request.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in request.tools
            ]
        return payload

    @staticmethod
    def _message(message: CanonicalMessage) -> dict[str, Any]:
        text_parts = [part.text or "" for part in message.content if part.kind is ContentKind.TEXT]
        image_parts = [part for part in message.content if part.kind is ContentKind.IMAGE]
        if image_parts:
            content: str | list[dict[str, Any]] = [
                *({"type": "text", "text": text} for text in text_parts),
                *(
                    {"type": "image_url", "image_url": {"url": part.image_url or part.data}}
                    for part in image_parts
                ),
            ]
        else:
            content = "\n".join(text_parts)
        result: dict[str, Any] = {"role": message.role, "content": content}
        if message.name:
            result["name"] = message.name
        if message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments},
                }
                for call in message.tool_calls
            ]
        tool_results = [part for part in message.content if part.kind is ContentKind.TOOL_RESULT]
        if tool_results:
            result["tool_call_id"] = tool_results[0].tool_call_id
            result["content"] = tool_results[0].text or json.dumps(tool_results[0].data)
        return result

    async def complete(self, request: CanonicalRequest, model: str) -> CanonicalResponse:
        response = await self.client.post(
            "chat/completions", json=self.request_payload(request, model), params=self.params
        )
        if response.is_error:
            self.health.failure(f"HTTP {response.status_code}")
            raise provider_error(response)
        try:
            result = self.response_from_payload(response.json())
        except (KeyError, TypeError, ValueError) as exc:
            self.health.failure("malformed response")
            raise ProviderError("provider returned a malformed chat completion") from exc
        self.health.success()
        return result

    @staticmethod
    def response_from_payload(payload: dict[str, Any]) -> CanonicalResponse:
        choice = payload["choices"][0]
        message = choice["message"]
        content = []
        if message.get("content") is not None:
            content.append(CanonicalContent(kind=ContentKind.TEXT, text=str(message["content"])))
        tool_calls = [
            CanonicalToolCall(
                id=call["id"],
                name=call["function"]["name"],
                arguments=call["function"].get("arguments", "{}"),
            )
            for call in message.get("tool_calls", [])
        ]
        usage = payload.get("usage") or {}
        return CanonicalResponse(
            id=payload.get("id", f"chatcmpl-{uuid4().hex}"),
            model=payload.get("model", "unknown"),
            message=CanonicalMessage(role="assistant", content=content, tool_calls=tool_calls),
            finish_reason=choice.get("finish_reason"),
            usage=TokenUsage(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                cached_input_tokens=(usage.get("prompt_tokens_details") or {}).get(
                    "cached_tokens", 0
                ),
            ),
            provider_response_id=payload.get("id"),
        )

    async def stream(self, request: CanonicalRequest, model: str) -> AsyncIterator[StreamEvent]:
        response_id = f"chatcmpl-{uuid4().hex}"
        emitted = False
        yield StreamEvent(type="response.start", response_id=response_id)
        try:
            async with self.client.stream(
                "POST",
                "chat/completions",
                json=self.request_payload(request.model_copy(update={"stream": True}), model),
                params=self.params,
            ) as response:
                if response.is_error:
                    await response.aread()
                    raise provider_error(response)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    payload = json.loads(data)
                    choice = payload.get("choices", [{}])[0]
                    delta = choice.get("delta", {})
                    if delta.get("content"):
                        emitted = True
                        yield StreamEvent(
                            type="content.delta",
                            response_id=response_id,
                            delta=delta["content"],
                        )
                    for call in delta.get("tool_calls", []):
                        function = call.get("function", {})
                        yield StreamEvent(
                            type="tool_call.delta",
                            response_id=response_id,
                            index=call.get("index", 0),
                            item={
                                "id": call.get("id"),
                                "name": function.get("name"),
                                "arguments": function.get("arguments", ""),
                            },
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
        payload = response.json()
        return [str(item["id"]) for item in payload.get("data", []) if item.get("id")]
