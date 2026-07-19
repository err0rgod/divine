"""Provider-neutral streaming lifecycle events."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StreamEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "response.start",
        "content.delta",
        "tool_call.start",
        "tool_call.delta",
        "response.complete",
        "response.error",
    ]
    response_id: str
    index: int = 0
    delta: str | None = None
    item: dict[str, Any] | None = None
    usage: dict[str, int] | None = None
    error: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
