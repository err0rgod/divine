"""Anthropic Messages request conversion and wire serialization."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

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


class AnthropicMessagesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    max_tokens: int = Field(ge=1)
    messages: list[dict[str, Any]]
    system: str | list[dict[str, Any]] | None = None
    temperature: float | None = Field(default=None, ge=0, le=1)
    top_p: float | None = Field(default=None, ge=0, le=1)
    top_k: int | None = Field(default=None, ge=1)
    stop_sequences: list[str] = Field(default_factory=list)
    stream: bool = False
    tools: list[dict[str, Any]] = Field(default_factory=list)
    tool_choice: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None

    def to_canonical(self) -> CanonicalRequest:
        messages: list[CanonicalMessage] = []
        if self.system:
            if isinstance(self.system, str):
                system_text = self.system
            else:
                system_text = "\n".join(
                    part.get("text", "")
                    for part in self.system
                    if part.get("type", "text") == "text"
                )
            messages.append(
                CanonicalMessage(
                    role="system",
                    content=[CanonicalContent(kind=ContentKind.TEXT, text=system_text)],
                )
            )
        messages.extend(_anthropic_message(message) for message in self.messages)
        return CanonicalRequest(
            model=self.model,
            messages=messages,
            stream=self.stream,
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=self.top_k,
            max_output_tokens=self.max_tokens,
            stop=self.stop_sequences,
            tools=[
                CanonicalTool(
                    name=tool["name"],
                    description=tool.get("description"),
                    parameters=tool.get("input_schema", {}),
                )
                for tool in self.tools
            ],
            tool_choice=self.tool_choice,
            metadata=self.metadata or {},
        )


def _anthropic_message(raw: dict[str, Any]) -> CanonicalMessage:
    role = raw.get("role")
    if role not in {"user", "assistant"}:
        raise CompatibilityError(
            "Anthropic message role must be user or assistant", "messages.role"
        )
    blocks = raw.get("content", [])
    if isinstance(blocks, str):
        blocks = [{"type": "text", "text": blocks}]
    contents: list[CanonicalContent] = []
    calls: list[CanonicalToolCall] = []
    for block in blocks:
        block_type = block.get("type")
        if block_type == "text":
            contents.append(CanonicalContent(kind=ContentKind.TEXT, text=block.get("text", "")))
        elif block_type == "image":
            source = block.get("source", {})
            if source.get("type") == "base64":
                contents.append(
                    CanonicalContent(
                        kind=ContentKind.IMAGE,
                        data=source.get("data"),
                        media_type=source.get("media_type"),
                    )
                )
            elif source.get("type") == "url":
                contents.append(
                    CanonicalContent(kind=ContentKind.IMAGE, image_url=source.get("url"))
                )
            else:
                raise CompatibilityError("unsupported Anthropic image source", "messages.content")
        elif block_type == "tool_use":
            calls.append(
                CanonicalToolCall(
                    id=block["id"],
                    name=block["name"],
                    arguments=json.dumps(block.get("input", {}), separators=(",", ":")),
                )
            )
        elif block_type == "tool_result":
            result = block.get("content", "")
            if isinstance(result, list):
                result = "\n".join(
                    part.get("text", "") for part in result if part.get("type") == "text"
                )
            contents.append(
                CanonicalContent(
                    kind=ContentKind.TOOL_RESULT,
                    tool_call_id=block["tool_use_id"],
                    text=str(result),
                )
            )
        else:
            raise CompatibilityError(
                f"unsupported Anthropic content block: {block_type}", "messages.content.type"
            )
    canonical_role = (
        "tool" if any(part.kind is ContentKind.TOOL_RESULT for part in contents) else role
    )
    return CanonicalMessage(role=canonical_role, content=contents, tool_calls=calls)


def serialize_response(response: CanonicalResponse) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = [
        {"type": "text", "text": part.text}
        for part in response.message.content
        if part.kind is ContentKind.TEXT
    ]
    blocks.extend(
        {
            "type": "tool_use",
            "id": call.id,
            "name": call.name,
            "input": json.loads(call.arguments),
        }
        for call in response.message.tool_calls
    )
    return {
        "id": response.id if response.id.startswith("msg_") else f"msg_{uuid4().hex}",
        "type": "message",
        "role": "assistant",
        "model": response.model,
        "content": blocks,
        "stop_reason": _stop_reason(response.finish_reason),
        "stop_sequence": None,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }


def _stop_reason(reason: str | None) -> str:
    return {
        "stop": "end_turn",
        "length": "max_tokens",
        "tool_calls": "tool_use",
    }.get(reason or "stop", reason or "end_turn")


def stream_event(name: str, payload: dict[str, Any]) -> str:
    data = {"type": name, **payload}
    return f"event: {name}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"
