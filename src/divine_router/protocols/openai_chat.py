"""OpenAI Chat Completions request conversion and response serialization."""

from __future__ import annotations

import json
import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from divine_router.errors import CompatibilityError
from divine_router.models.canonical import (
    CanonicalContent,
    CanonicalMessage,
    CanonicalRequest,
    CanonicalResponse,
    CanonicalTool,
    CanonicalToolCall,
    ContentKind,
)


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    messages: list[dict[str, Any]]
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, ge=0, le=1)
    max_tokens: int | None = Field(default=None, ge=1)
    max_completion_tokens: int | None = Field(default=None, ge=1)
    stop: str | list[str] | None = None
    stream: bool = False
    stream_options: dict[str, Any] | None = None
    tools: list[dict[str, Any]] = Field(default_factory=list)
    tool_choice: str | dict[str, Any] | None = None
    response_format: dict[str, Any] | None = None
    seed: int | None = None
    user: str | None = None

    @model_validator(mode="after")
    def validate_token_fields(self) -> ChatCompletionRequest:
        if self.max_tokens is not None and self.max_completion_tokens is not None:
            raise ValueError("max_tokens and max_completion_tokens are mutually exclusive")
        return self

    def to_canonical(self) -> CanonicalRequest:
        return CanonicalRequest(
            model=self.model,
            messages=[_message(message) for message in self.messages],
            stream=self.stream,
            temperature=self.temperature,
            top_p=self.top_p,
            max_output_tokens=self.max_completion_tokens or self.max_tokens,
            stop=[self.stop] if isinstance(self.stop, str) else self.stop or [],
            tools=[_tool(tool) for tool in self.tools],
            tool_choice=self.tool_choice,
            response_format=self.response_format,
            seed=self.seed,
            metadata={"client_user": self.user} if self.user else {},
        )


def _message(raw: dict[str, Any]) -> CanonicalMessage:
    role = raw.get("role")
    if role not in {"system", "developer", "user", "assistant", "tool"}:
        raise CompatibilityError("unsupported Chat Completions message role", "messages.role")
    contents: list[CanonicalContent] = []
    content = raw.get("content")
    if isinstance(content, str):
        contents.append(CanonicalContent(kind=ContentKind.TEXT, text=content))
    elif isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                raise CompatibilityError(
                    "message content parts must be objects", "messages.content"
                )
            part_type = part.get("type")
            if part_type in {"text", "input_text"}:
                contents.append(CanonicalContent(kind=ContentKind.TEXT, text=part.get("text", "")))
            elif part_type in {"image_url", "input_image"}:
                image = part.get("image_url")
                url = image.get("url") if isinstance(image, dict) else image
                contents.append(CanonicalContent(kind=ContentKind.IMAGE, image_url=url))
            else:
                raise CompatibilityError(
                    f"unsupported Chat Completions content type: {part_type}",
                    "messages.content.type",
                )
    elif content is not None:
        raise CompatibilityError("message content must be text or an array", "messages.content")
    if role == "tool":
        if not raw.get("tool_call_id"):
            raise CompatibilityError("tool messages require tool_call_id", "messages.tool_call_id")
        text = contents[0].text if contents else ""
        contents = [
            CanonicalContent(
                kind=ContentKind.TOOL_RESULT,
                tool_call_id=raw["tool_call_id"],
                text=text,
            )
        ]
    calls = []
    for call in raw.get("tool_calls", []):
        if call.get("type", "function") != "function":
            raise CompatibilityError(
                "only function tool calls are supported", "messages.tool_calls"
            )
        function = call.get("function", {})
        calls.append(
            CanonicalToolCall(
                id=call["id"],
                name=function["name"],
                arguments=function.get("arguments", "{}"),
            )
        )
    return CanonicalMessage(role=role, content=contents, tool_calls=calls, name=raw.get("name"))


def _tool(raw: dict[str, Any]) -> CanonicalTool:
    if raw.get("type") != "function" or not isinstance(raw.get("function"), dict):
        raise CompatibilityError("only function tools are supported", "tools")
    function = raw["function"]
    return CanonicalTool(
        name=function["name"],
        description=function.get("description"),
        parameters=function.get("parameters", {}),
    )


def serialize_response(response: CanonicalResponse) -> dict[str, Any]:
    text = "".join(
        part.text or "" for part in response.message.content if part.kind is ContentKind.TEXT
    )
    message: dict[str, Any] = {"role": "assistant", "content": text or None}
    if response.message.tool_calls:
        message["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": call.arguments},
            }
            for call in response.message.tool_calls
        ]
    return {
        "id": response.id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": response.model,
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": response.finish_reason or "stop",
                "logprobs": None,
            }
        ],
        "usage": {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.total_tokens,
        },
    }


def stream_chunk(
    response_id: str,
    model: str,
    delta: str | None,
    finish: bool = False,
    *,
    tool_call: dict[str, Any] | None = None,
    tool_index: int = 0,
    finish_reason: str | None = None,
) -> str:
    delta_payload: dict[str, Any] = {"content": delta} if delta is not None else {}
    if tool_call is not None:
        function = {
            key: tool_call[key] for key in ("name", "arguments") if tool_call.get(key) is not None
        }
        call = {"index": tool_index, "function": function}
        if tool_call.get("id"):
            call.update({"id": tool_call["id"], "type": "function"})
        delta_payload["tool_calls"] = [call]
    payload = {
        "id": response_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": delta_payload,
                "finish_reason": finish_reason or ("stop" if finish else None),
            }
        ],
    }
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"
