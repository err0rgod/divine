"""Local rule-based task classifier used when no optional LLM classifier runs."""

from __future__ import annotations

import re
from enum import StrEnum

from divine_router.models.canonical import CanonicalRequest, ContentKind


class TaskClass(StrEnum):
    SIMPLE_CHAT = "simple-chat"
    EXTRACTION = "extraction"
    SUMMARIZATION = "summarization"
    CODING = "coding"
    DEBUGGING = "debugging"
    AGENTIC_TOOL_USE = "agentic-tool-use"
    MATHEMATICAL_REASONING = "mathematical-reasoning"
    DEEP_REASONING = "deep-reasoning"
    LONG_CONTEXT = "long-context-analysis"
    CREATIVE_WRITING = "creative-writing"
    VISION = "vision"
    LOW_LATENCY = "low-latency"
    LOW_COST = "low-cost"


PATTERNS: tuple[tuple[TaskClass, re.Pattern[str]], ...] = (
    (TaskClass.DEBUGGING, re.compile(r"\b(debug|traceback|stack trace|bug|exception)\b", re.I)),
    (
        TaskClass.CODING,
        re.compile(r"\b(code|function|class|refactor|implement|repository)\b", re.I),
    ),
    (TaskClass.SUMMARIZATION, re.compile(r"\b(summarize|summary|condense|tl;?dr)\b", re.I)),
    (TaskClass.EXTRACTION, re.compile(r"\b(extract|parse|fields?|entities|json)\b", re.I)),
    (
        TaskClass.MATHEMATICAL_REASONING,
        re.compile(r"\b(prove|equation|integral|theorem|calculate)\b", re.I),
    ),
    (
        TaskClass.DEEP_REASONING,
        re.compile(r"\b(analyze deeply|step by step|reasoning|trade-?offs)\b", re.I),
    ),
    (TaskClass.CREATIVE_WRITING, re.compile(r"\b(story|poem|creative|screenplay|fiction)\b", re.I)),
)


def classify(request: CanonicalRequest) -> TaskClass:
    if any(
        part.kind is ContentKind.IMAGE for message in request.messages for part in message.content
    ):
        return TaskClass.VISION
    if request.tools:
        return TaskClass.AGENTIC_TOOL_USE
    text = "\n".join(
        part.text or ""
        for message in request.messages
        for part in message.content
        if part.kind is ContentKind.TEXT
    )
    if len(text) > 50_000:
        return TaskClass.LONG_CONTEXT
    for task_class, pattern in PATTERNS:
        if pattern.search(text):
            return task_class
    return TaskClass.SIMPLE_CHAT
