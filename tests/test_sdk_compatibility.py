from __future__ import annotations

from typing import cast

import anthropic
import openai
import pytest
from fastapi.testclient import TestClient
from openai.types.chat import ChatCompletionMessageFunctionToolCall

from divine_router.api.app import create_app
from divine_router.service import Gateway

TOKEN = "divine_sdk_test_token_that_is_long_enough"


@pytest.fixture
def transport(gateway: Gateway) -> TestClient:
    return TestClient(create_app(gateway.config, gateway, TOKEN))


@pytest.mark.sdk
def test_openai_sdk_chat_nonstream_stream_and_tools(
    gateway: Gateway, transport: TestClient
) -> None:
    client = openai.OpenAI(
        api_key=TOKEN,
        base_url="http://testserver/v1",
        http_client=transport,
    )
    completion = client.chat.completions.create(
        model="mock/demo", messages=[{"role": "user", "content": "hello"}]
    )
    assert completion.choices[0].message.content == "DIVINE_OK"

    chunks = list(
        client.chat.completions.create(
            model="mock/demo",
            messages=[{"role": "user", "content": "hello"}],
            stream=True,
        )
    )
    assert "".join(chunk.choices[0].delta.content or "" for chunk in chunks) == "DIVINE_OK"

    tool_completion = client.chat.completions.create(
        model="mock/demo",
        messages=[{"role": "user", "content": "use a tool"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "lookup",
                    "description": "Lookup",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
    )
    calls = tool_completion.choices[0].message.tool_calls
    assert calls
    function_call = cast(ChatCompletionMessageFunctionToolCall, calls[0])
    assert function_call.function.name == "lookup"


@pytest.mark.sdk
def test_openai_sdk_responses(gateway: Gateway, transport: TestClient) -> None:
    client = openai.OpenAI(
        api_key=TOKEN,
        base_url="http://testserver/v1",
        http_client=transport,
    )
    response = client.responses.create(model="mock/demo", input="hello")
    assert response.output_text == "DIVINE_OK"


@pytest.mark.sdk
def test_anthropic_sdk_messages_nonstream_stream_and_tools(
    gateway: Gateway, transport: TestClient
) -> None:
    client = anthropic.Anthropic(
        api_key=TOKEN,
        base_url="http://testserver",
        http_client=transport,
    )
    message = client.messages.create(
        model="mock/demo",
        max_tokens=20,
        messages=[{"role": "user", "content": "hello"}],
    )
    assert message.content[0].text == "DIVINE_OK"  # type: ignore[union-attr]

    with client.messages.stream(
        model="mock/demo",
        max_tokens=20,
        messages=[{"role": "user", "content": "hello"}],
    ) as stream:
        assert stream.get_final_text() == "DIVINE_OK"

    tool_message = client.messages.create(
        model="mock/demo",
        max_tokens=20,
        messages=[{"role": "user", "content": "use a tool"}],
        tools=[
            {
                "name": "lookup",
                "description": "Lookup",
                "input_schema": {"type": "object", "properties": {}},
            }
        ],
    )
    assert tool_message.content[0].type == "tool_use"
