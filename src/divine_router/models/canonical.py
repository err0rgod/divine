"""Provider-neutral request and response models.

Protocol parsers translate into these objects. Provider adapters consume them,
which keeps wire compatibility concerns out of provider-specific HTTP code.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContentKind(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    TOOL_RESULT = "tool_result"


class CanonicalContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ContentKind
    text: str | None = None
    image_url: str | None = None
    media_type: str | None = None
    tool_call_id: str | None = None
    data: Any = None

    @model_validator(mode="after")
    def validate_payload(self) -> CanonicalContent:
        if self.kind is ContentKind.TEXT and self.text is None:
            raise ValueError("text content requires text")
        if self.kind is ContentKind.IMAGE and self.image_url is None and self.data is None:
            raise ValueError("image content requires image_url or data")
        if self.kind is ContentKind.TOOL_RESULT and not self.tool_call_id:
            raise ValueError("tool result content requires tool_call_id")
        return self


class CanonicalToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    arguments: str


class CanonicalMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "developer", "user", "assistant", "tool"]
    content: list[CanonicalContent] = Field(default_factory=list)
    tool_calls: list[CanonicalToolCall] = Field(default_factory=list)
    name: str | None = None


class CanonicalTool(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class CanonicalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    messages: list[CanonicalMessage]
    stream: bool = False
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, ge=0, le=1)
    top_k: int | None = Field(default=None, ge=1)
    max_output_tokens: int | None = Field(default=None, ge=1)
    stop: list[str] = Field(default_factory=list)
    tools: list[CanonicalTool] = Field(default_factory=list)
    tool_choice: str | dict[str, Any] | None = None
    response_format: dict[str, Any] | None = None
    seed: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TokenUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class CanonicalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    model: str
    message: CanonicalMessage
    finish_reason: str | None = None
    usage: TokenUsage = Field(default_factory=TokenUsage)
    provider_response_id: str | None = None
