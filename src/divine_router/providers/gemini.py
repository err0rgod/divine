"""Google Gemini generateContent adapter."""

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
    ContentKind,
    TokenUsage,
)
from divine_router.models.streaming import StreamEvent
from divine_router.providers.base import Provider, ProviderHealth
from divine_router.providers.http import authentication, provider_error


class GeminiProvider(Provider):
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
    def request_payload(request: CanonicalRequest) -> dict[str, Any]:
        system_parts: list[dict[str, str]] = []
        contents: list[dict[str, Any]] = []
        for message in request.messages:
            parts: list[dict[str, Any]] = []
            for part in message.content:
                if part.kind is ContentKind.TEXT:
                    parts.append({"text": part.text})
                elif part.kind is ContentKind.IMAGE:
                    parts.append(
                        {
                            "inlineData": {
                                "mimeType": part.media_type,
                                "data": part.data,
                            }
                        }
                    )
            if message.role in {"system", "developer"}:
                system_parts.extend(parts)
            else:
                contents.append(
                    {"role": "model" if message.role == "assistant" else "user", "parts": parts}
                )
        payload: dict[str, Any] = {"contents": contents}
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}
        generation = {
            "temperature": request.temperature,
            "topP": request.top_p,
            "topK": request.top_k,
            "maxOutputTokens": request.max_output_tokens,
            "stopSequences": request.stop or None,
        }
        payload["generationConfig"] = {
            key: value for key, value in generation.items() if value is not None
        }
        if request.tools:
            payload["tools"] = [
                {
                    "functionDeclarations": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.parameters,
                        }
                        for tool in request.tools
                    ]
                }
            ]
        return payload

    async def complete(self, request: CanonicalRequest, model: str) -> CanonicalResponse:
        response = await self.client.post(
            f"models/{model}:generateContent",
            json=self.request_payload(request),
            params=self.params,
        )
        if response.is_error:
            raise provider_error(response)
        try:
            payload = response.json()
            candidate = payload["candidates"][0]
            text = "".join(part.get("text", "") for part in candidate["content"].get("parts", []))
            usage = payload.get("usageMetadata", {})
            result = CanonicalResponse(
                id=f"gemini-{uuid4().hex}",
                model=model,
                message=CanonicalMessage(
                    role="assistant",
                    content=[CanonicalContent(kind=ContentKind.TEXT, text=text)],
                ),
                finish_reason=candidate.get("finishReason"),
                usage=TokenUsage(
                    input_tokens=usage.get("promptTokenCount", 0),
                    output_tokens=usage.get("candidatesTokenCount", 0),
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError("provider returned a malformed Gemini response") from exc
        self.health.success()
        return result

    async def stream(self, request: CanonicalRequest, model: str) -> AsyncIterator[StreamEvent]:
        response_id = f"gemini-{uuid4().hex}"
        input_tokens = 0
        output_tokens = 0
        yield StreamEvent(type="response.start", response_id=response_id)
        try:
            async with self.client.stream(
                "POST",
                f"models/{model}:streamGenerateContent",
                json=self.request_payload(request),
                params={**self.params, "alt": "sse"},
            ) as response:
                if response.is_error:
                    await response.aread()
                    raise provider_error(response)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    payload = json.loads(line[5:].strip())
                    raw_usage = payload.get("usageMetadata") or {}
                    input_tokens = int(raw_usage.get("promptTokenCount", input_tokens))
                    output_tokens = int(raw_usage.get("candidatesTokenCount", output_tokens))
                    for part in (
                        payload.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    ):
                        if part.get("text"):
                            yield StreamEvent(
                                type="content.delta",
                                response_id=response_id,
                                delta=part["text"],
                            )
                        function_call = part.get("functionCall")
                        if function_call:
                            yield StreamEvent(
                                type="tool_call.start",
                                response_id=response_id,
                                item={
                                    "id": f"call_{uuid4().hex}",
                                    "name": function_call.get("name"),
                                    "arguments": json.dumps(
                                        function_call.get("args", {}), separators=(",", ":")
                                    ),
                                },
                            )
            self.health.success()
            yield StreamEvent(
                type="response.complete",
                response_id=response_id,
                usage={"input_tokens": input_tokens, "output_tokens": output_tokens},
            )
        except (httpx.HTTPError, json.JSONDecodeError, ProviderError) as exc:
            self.health.failure(type(exc).__name__)
            if isinstance(exc, ProviderError):
                raise
            raise ProviderError("provider stream failed") from exc

    async def discover_models(self) -> list[str]:
        response = await self.client.get("models", params=self.params)
        if response.is_error:
            raise provider_error(response)
        return [item["name"].removeprefix("models/") for item in response.json().get("models", [])]
