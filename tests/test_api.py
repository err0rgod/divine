from __future__ import annotations

from fastapi.testclient import TestClient

from divine_router.api.app import create_app
from divine_router.config.models import ServerConfig
from divine_router.persistence.database import Database
from divine_router.service import Gateway

TOKEN = "divine_test_token_that_is_long_enough"


def client(gateway: Gateway, database: Database | None = None) -> TestClient:
    return TestClient(create_app(gateway.config, gateway, TOKEN, database))


def test_authentication_is_required(gateway: Gateway) -> None:
    response = client(gateway).get("/healthz")
    assert response.status_code == 401
    assert response.json()["error"]["type"] == "authentication_error"


def test_chat_completion_and_route_headers(gateway: Gateway) -> None:
    response = client(gateway).post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"model": "mock/demo", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "DIVINE_OK"
    assert response.headers["x-divine-provider"] == "mock"
    assert response.headers["x-divine-request-id"].startswith("req_")


def test_chat_streaming(gateway: Gateway) -> None:
    with client(gateway).stream(
        "POST",
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={
            "model": "mock/demo",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": True,
        },
    ) as response:
        body = "".join(response.iter_text())
    assert "DIVINE_" in body
    assert "data: [DONE]" in body


def test_streaming_tool_calls_across_protocols(gateway: Gateway) -> None:
    tool = {
        "type": "function",
        "function": {
            "name": "lookup",
            "description": "Lookup",
            "parameters": {"type": "object", "properties": {}},
        },
    }
    headers = {"Authorization": f"Bearer {TOKEN}"}
    chat = client(gateway).post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": "mock/demo",
            "messages": [{"role": "user", "content": "use a tool"}],
            "tools": [tool],
            "stream": True,
        },
    )
    assert '"tool_calls"' in chat.text
    assert '"finish_reason":"tool_calls"' in chat.text

    responses = client(gateway).post(
        "/v1/responses",
        headers=headers,
        json={
            "model": "mock/demo",
            "input": "use a tool",
            "tools": [
                {
                    "type": "function",
                    "name": "lookup",
                    "description": "Lookup",
                    "parameters": {"type": "object", "properties": {}},
                }
            ],
            "stream": True,
        },
    )
    assert "event: response.function_call_arguments.delta" in responses.text
    assert '"arguments":"{\\"value\\":1}"' in responses.text

    messages = client(gateway).post(
        "/v1/messages",
        headers={"x-api-key": TOKEN},
        json={
            "model": "mock/demo",
            "max_tokens": 20,
            "messages": [{"role": "user", "content": "use a tool"}],
            "tools": [
                {
                    "name": "lookup",
                    "description": "Lookup",
                    "input_schema": {"type": "object", "properties": {}},
                }
            ],
            "stream": True,
        },
    )
    assert '"type":"tool_use"' in messages.text
    assert '"type":"input_json_delta"' in messages.text
    assert '"stop_reason":"tool_use"' in messages.text


def test_responses_nonstream_and_lifecycle_stream(gateway: Gateway) -> None:
    standard = client(gateway).post(
        "/v1/responses",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"model": "mock/demo", "input": "hello"},
    )
    assert standard.status_code == 200
    assert standard.json()["object"] == "response"
    assert standard.json()["output_text"] == "DIVINE_OK"

    streamed = client(gateway).post(
        "/v1/responses",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"model": "mock/demo", "input": "hello", "stream": True},
    )
    assert "event: response.created" in streamed.text
    assert "event: response.output_text.delta" in streamed.text
    assert "event: response.completed" in streamed.text


def test_anthropic_messages_and_key_header(gateway: Gateway) -> None:
    response = client(gateway).post(
        "/v1/messages",
        headers={"x-api-key": TOKEN, "anthropic-version": "2023-06-01"},
        json={
            "model": "mock/demo",
            "max_tokens": 20,
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    assert response.status_code == 200
    assert response.json()["type"] == "message"
    assert response.json()["content"][0]["text"] == "DIVINE_OK"


def test_auto_route_controls_and_admin_endpoints(gateway: Gateway) -> None:
    headers = {"Authorization": f"Bearer {TOKEN}", "x-divine-prefer": "latency"}
    routed = client(gateway).post(
        "/v1/auto/chat/completions",
        headers=headers,
        json={"model": "ignored", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert routed.status_code == 200
    assert routed.headers["x-divine-route"].startswith("auto:")
    assert client(gateway).get("/v1/models", headers=headers).json()["data"]
    assert client(gateway).get("/v1/divine/providers", headers=headers).status_code == 200


def test_invalid_control_and_anthropic_error_shape(gateway: Gateway) -> None:
    invalid = client(gateway).post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {TOKEN}", "x-divine-max-cost": "nope"},
        json={"model": "mock/demo", "messages": []},
    )
    assert invalid.status_code == 400
    anth = client(gateway).post(
        "/v1/messages",
        headers={"x-api-key": TOKEN},
        json={"model": "mock/demo", "messages": []},
    )
    assert anth.status_code == 400
    assert anth.json()["type"] == "error"


def test_body_limit_checks_actual_bytes_and_request_id_is_sanitized(gateway: Gateway) -> None:
    config = gateway.config.model_copy(
        update={"server": ServerConfig(request_body_limit_bytes=1024)}
    )
    api_client = TestClient(create_app(config, gateway, TOKEN))
    response = api_client.post(
        "/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "content-length": "0",
            "x-request-id": "invalid request id with spaces",
        },
        content=b"x" * 2048,
    )
    assert response.status_code == 413
    assert response.headers["x-divine-request-id"].startswith("req_")


def test_completed_stream_records_usage_and_first_token(
    gateway: Gateway, database: Database
) -> None:
    with client(gateway, database) as api_client:
        response = api_client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={
                "model": "mock/demo",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True,
            },
        )
    assert response.status_code == 200
    records = database.recent_usage()
    assert len(records) == 1
    assert records[0].input_tokens == 3
    assert records[0].output_tokens == 2
    assert records[0].time_to_first_token_ms is not None
