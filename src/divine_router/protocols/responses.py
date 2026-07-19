"""Explicit OpenAI Responses API item converters and serializers."""

from __future__ import annotations

import json
import time
from typing import Any
from uuid import uuid4

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


class ResponsesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    input: str | list[dict[str, Any]]
    instructions: str | None = None
    stream: bool = False
    tools: list[dict[str, Any]] = Field(default_factory=list)
    tool_choice: str | dict[str, Any] | None = None
    max_output_tokens: int | None = Field(default=None, ge=1)
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, ge=0, le=1)
    reasoning: dict[str, Any] | None = None
    text: dict[str, Any] | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    parallel_tool_calls: bool = True
    store: bool = False
    previous_response_id: str | None = None
    conversation: str | dict[str, Any] | None = None
    background: bool = False
    include: list[str] | None = None
    truncation: str | None = None

    @model_validator(mode="after")
    def reject_stateful_features(self) -> ResponsesRequest:
        unsupported = {
            "previous_response_id": self.previous_response_id,
            "conversation": self.conversation,
            "store": self.store,
            "background": self.background,
        }
        for field, value in unsupported.items():
            if value:
                raise ValueError(f"{field} is stateful and is not supported by Divine Router")
        return self

    def to_canonical(self) -> CanonicalRequest:
        messages: list[CanonicalMessage] = []
        if self.instructions:
            messages.append(
                CanonicalMessage(
                    role="developer",
                    content=[CanonicalContent(kind=ContentKind.TEXT, text=self.instructions)],
                )
            )
        if isinstance(self.input, str):
            messages.append(
                CanonicalMessage(
                    role="user", content=[CanonicalContent(kind=ContentKind.TEXT, text=self.input)]
                )
            )
        else:
            messages.extend(_input_items(self.input))
        response_format = self.text.get("format") if self.text else None
        metadata: dict[str, Any] = dict(self.metadata)
        if self.reasoning:
            metadata["reasoning"] = self.reasoning
        metadata["parallel_tool_calls"] = self.parallel_tool_calls
        return CanonicalRequest(
            model=self.model,
            messages=messages,
            stream=self.stream,
            temperature=self.temperature,
            top_p=self.top_p,
            max_output_tokens=self.max_output_tokens,
            tools=[_response_tool(tool) for tool in self.tools],
            tool_choice=self.tool_choice,
            response_format=response_format,
            metadata=metadata,
        )


def _input_items(items: list[dict[str, Any]]) -> list[CanonicalMessage]:
    messages: list[CanonicalMessage] = []
    for item in items:
        item_type = item.get("type", "message")
        if item_type == "message":
            role = item.get("role", "user")
            if role not in {"user", "assistant", "system", "developer"}:
                raise CompatibilityError("unsupported Responses message role", "input.role")
            messages.append(
                CanonicalMessage(role=role, content=_response_content(item.get("content", [])))
            )
        elif item_type == "function_call":
            messages.append(
                CanonicalMessage(
                    role="assistant",
                    tool_calls=[
                        CanonicalToolCall(
                            id=item.get("call_id") or item.get("id") or f"call_{uuid4().hex}",
                            name=item["name"],
                            arguments=item.get("arguments", "{}"),
                        )
                    ],
                )
            )
        elif item_type == "function_call_output":
            output = item.get("output", "")
            text = output if isinstance(output, str) else json.dumps(output)
            messages.append(
                CanonicalMessage(
                    role="tool",
                    content=[
                        CanonicalContent(
                            kind=ContentKind.TOOL_RESULT,
                            tool_call_id=item.get("call_id") or item.get("id"),
                            text=text,
                        )
                    ],
                )
            )
        elif item_type == "reasoning":
            summary = item.get("summary", [])
            text = "\n".join(part.get("text", "") for part in summary if isinstance(part, dict))
            if text:
                messages.append(
                    CanonicalMessage(
                        role="assistant",
                        content=[CanonicalContent(kind=ContentKind.TEXT, text=text)],
                    )
                )
        else:
            raise CompatibilityError(
                f"unsupported Responses input item type: {item_type}", "input.type"
            )
    return messages


def _response_content(raw: str | list[dict[str, Any]]) -> list[CanonicalContent]:
    if isinstance(raw, str):
        return [CanonicalContent(kind=ContentKind.TEXT, text=raw)]
    content: list[CanonicalContent] = []
    for part in raw:
        part_type = part.get("type")
        if part_type in {"input_text", "output_text"}:
            content.append(CanonicalContent(kind=ContentKind.TEXT, text=part.get("text", "")))
        elif part_type == "input_image":
            content.append(
                CanonicalContent(
                    kind=ContentKind.IMAGE,
                    image_url=part.get("image_url"),
                    data=part.get("file_id"),
                )
            )
        else:
            raise CompatibilityError(
                f"unsupported Responses content type: {part_type}", "input.content.type"
            )
    return content


def _response_tool(raw: dict[str, Any]) -> CanonicalTool:
    if raw.get("type") != "function":
        raise CompatibilityError(
            f"hosted Responses tool {raw.get('type')} is not supported", "tools.type"
        )
    return CanonicalTool(
        name=raw["name"],
        description=raw.get("description"),
        parameters=raw.get("parameters", {}),
    )


def serialize_response(response: CanonicalResponse, request: ResponsesRequest) -> dict[str, Any]:
    output: list[dict[str, Any]] = []
    text = "".join(
        part.text or "" for part in response.message.content if part.kind is ContentKind.TEXT
    )
    if text:
        output.append(
            {
                "id": f"msg_{uuid4().hex}",
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            }
        )
    output.extend(
        {
            "id": f"fc_{uuid4().hex}",
            "type": "function_call",
            "status": "completed",
            "call_id": call.id,
            "name": call.name,
            "arguments": call.arguments,
        }
        for call in response.message.tool_calls
    )
    reasoning = request.reasoning or {"effort": None, "summary": None}
    return {
        "id": response.id.replace("chatcmpl-", "resp_"),
        "object": "response",
        "created_at": int(time.time()),
        "status": "completed",
        "error": None,
        "incomplete_details": None,
        "instructions": request.instructions,
        "max_output_tokens": request.max_output_tokens,
        "model": response.model,
        "output": output,
        "output_text": text,
        "parallel_tool_calls": request.parallel_tool_calls,
        "previous_response_id": None,
        "reasoning": reasoning,
        "store": False,
        "temperature": request.temperature,
        "text": request.text or {"format": {"type": "text"}},
        "tool_choice": request.tool_choice or "auto",
        "tools": request.tools,
        "top_p": request.top_p,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "input_tokens_details": {"cached_tokens": response.usage.cached_input_tokens},
            "output_tokens": response.usage.output_tokens,
            "output_tokens_details": {"reasoning_tokens": 0},
            "total_tokens": response.usage.total_tokens,
        },
        "metadata": request.metadata,
    }


def event(name: str, payload: dict[str, Any]) -> str:
    data = {"type": name, **payload}
    return f"event: {name}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"
