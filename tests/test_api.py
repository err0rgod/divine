from __future__ import annotations

from fastapi.testclient import TestClient

from divine_router.api.app import create_app
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
