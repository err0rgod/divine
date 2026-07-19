from __future__ import annotations

import pytest
from pydantic import ValidationError

from divine_router.errors import CompatibilityError
from divine_router.models.canonical import ContentKind
from divine_router.protocols.anthropic_messages import AnthropicMessagesRequest
from divine_router.protocols.openai_chat import ChatCompletionRequest
from divine_router.protocols.responses import ResponsesRequest


def test_chat_conversion_preserves_tools_images_and_limits() -> None:
    request = ChatCompletionRequest.model_validate(
        {
            "model": "mock/demo",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "describe"},
                        {"type": "image_url", "image_url": {"url": "https://example.test/x.png"}},
                    ],
                }
            ],
            "max_completion_tokens": 50,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "lookup",
                        "description": "Lookup data",
                        "parameters": {"type": "object"},
                    },
                }
            ],
        }
    ).to_canonical()
    assert request.max_output_tokens == 50
    assert request.tools[0].name == "lookup"
    assert request.messages[0].content[1].kind is ContentKind.IMAGE


def test_chat_rejects_silently_dropped_audio() -> None:
    body = ChatCompletionRequest(
        model="mock/demo",
        messages=[{"role": "user", "content": [{"type": "input_audio", "data": "abc"}]}],
    )
    with pytest.raises(CompatibilityError, match="input_audio"):
        body.to_canonical()


def test_responses_converter_handles_calls_and_outputs() -> None:
    request = ResponsesRequest(
        model="mock/demo",
        instructions="Be precise",
        input=[
            {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "go"}]},
            {"type": "function_call", "call_id": "call_1", "name": "lookup", "arguments": "{}"},
            {"type": "function_call_output", "call_id": "call_1", "output": "done"},
        ],
        reasoning={"effort": "low"},
    ).to_canonical()
    assert [message.role for message in request.messages] == [
        "developer",
        "user",
        "assistant",
        "tool",
    ]
    assert request.metadata["reasoning"] == {"effort": "low"}


def test_responses_rejects_hosted_and_stateful_features() -> None:
    with pytest.raises(ValidationError, match="previous_response_id"):
        ResponsesRequest(model="mock/demo", input="hi", previous_response_id="resp_old")
    body = ResponsesRequest(model="mock/demo", input="hi", tools=[{"type": "web_search_preview"}])
    with pytest.raises(CompatibilityError, match="hosted"):
        body.to_canonical()


def test_anthropic_conversion_preserves_tool_blocks() -> None:
    request = AnthropicMessagesRequest(
        model="mock/demo",
        max_tokens=40,
        messages=[
            {
                "role": "assistant",
                "content": [{"type": "tool_use", "id": "call_1", "name": "lookup", "input": {}}],
            },
            {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "call_1", "content": "ok"}],
            },
        ],
    ).to_canonical()
    assert request.messages[0].tool_calls[0].name == "lookup"
    assert request.messages[1].content[0].tool_call_id == "call_1"
