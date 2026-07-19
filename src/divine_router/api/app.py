"""Authenticated OpenAI, Responses, Anthropic, and administration APIs."""

from __future__ import annotations

import math
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter, time
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response, StreamingResponse

from divine_router.config.models import DivineConfig
from divine_router.errors import DivineError
from divine_router.models.canonical import CanonicalRequest
from divine_router.persistence.database import Database, UsageRecord
from divine_router.protocols.anthropic_messages import (
    AnthropicMessagesRequest,
)
from divine_router.protocols.anthropic_messages import (
    serialize_response as anthropic_response,
)
from divine_router.protocols.anthropic_messages import (
    stream_event as anthropic_event,
)
from divine_router.protocols.openai_chat import (
    ChatCompletionRequest,
    stream_chunk,
)
from divine_router.protocols.openai_chat import (
    serialize_response as chat_response,
)
from divine_router.protocols.responses import (
    ResponsesRequest,
)
from divine_router.protocols.responses import (
    event as responses_event,
)
from divine_router.protocols.responses import (
    serialize_response as responses_response,
)
from divine_router.security.auth import authenticate_request
from divine_router.security.rate_limit import RateLimiter
from divine_router.service import Gateway, RouteMetadata


def create_app(
    config: DivineConfig,
    gateway: Gateway,
    api_token: str,
    database: Database | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if database:
            database.initialize()
        try:
            yield
        finally:
            if database:
                database.close()

    app = FastAPI(title="Divine Router", version="0.1.0", lifespan=lifespan)
    app.state.gateway = gateway
    app.state.api_token = api_token
    app.state.database = database
    limiter = RateLimiter(config.server.rate_limit_per_minute)

    @app.middleware("http")
    async def security_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = _request_id(request.headers.get("x-request-id"))
        request.state.request_id = request_id
        try:
            authenticate_request(request, api_token)
            client = request.client.host if request.client else "local"
            limiter.check(client)
            content_length = request.headers.get("content-length")
            if content_length is not None:
                try:
                    declared_length = int(content_length)
                except ValueError as exc:
                    raise DivineError("content-length must be an integer", param="header") from exc
                if declared_length < 0:
                    raise DivineError("content-length cannot be negative", param="header")
                if declared_length > config.server.request_body_limit_bytes:
                    raise DivineError("request body is too large", status_code=413)
            body = await request.body()
            if len(body) > config.server.request_body_limit_bytes:
                raise DivineError("request body is too large", status_code=413)
            response = await call_next(request)
        except DivineError as exc:
            response = _error_response(request, exc)
        response.headers["x-divine-request-id"] = request_id
        return response

    @app.exception_handler(DivineError)
    async def divine_error_handler(request: Request, exc: DivineError) -> JSONResponse:
        return _error_response(request, exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        message = "; ".join(error["msg"] for error in exc.errors())
        return _error_response(request, DivineError(message, param="body"))

    @app.get("/healthz")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def ready() -> JSONResponse:
        ready_state = bool(gateway.providers and gateway.registry.all())
        return JSONResponse(
            {"status": "ready" if ready_state else "not-ready"},
            status_code=200 if ready_state else 503,
        )

    @app.post("/v1/chat/completions")
    @app.post("/v1/auto/chat/completions")
    async def chat(request: Request, body: ChatCompletionRequest) -> Response:
        canonical = body.to_canonical()
        if request.url.path.startswith("/v1/auto/"):
            canonical = canonical.model_copy(update={"model": "auto"})
        if canonical.stream:
            started = perf_counter()
            events, metadata = await gateway.stream(canonical, _constraints(request))
            return StreamingResponse(
                _chat_stream(
                    _metered_events(request, canonical, metadata, events, started), metadata.model
                ),
                media_type="text/event-stream",
                headers=_route_headers(metadata),
            )
        started = perf_counter()
        response, metadata = await gateway.complete(canonical, _constraints(request))
        _meter(
            request,
            canonical,
            metadata,
            response.usage.input_tokens,
            response.usage.output_tokens,
            started,
        )
        return JSONResponse(chat_response(response), headers=_route_headers(metadata))

    @app.post("/v1/responses")
    async def responses(request: Request, body: ResponsesRequest) -> Response:
        canonical = body.to_canonical()
        if canonical.stream:
            started = perf_counter()
            events, metadata = await gateway.stream(canonical, _constraints(request))
            return StreamingResponse(
                _responses_stream(
                    _metered_events(request, canonical, metadata, events, started),
                    metadata.model,
                    body,
                ),
                media_type="text/event-stream",
                headers=_route_headers(metadata),
            )
        started = perf_counter()
        response, metadata = await gateway.complete(canonical, _constraints(request))
        _meter(
            request,
            canonical,
            metadata,
            response.usage.input_tokens,
            response.usage.output_tokens,
            started,
        )
        return JSONResponse(responses_response(response, body), headers=_route_headers(metadata))

    @app.post("/v1/messages")
    async def messages(request: Request, body: AnthropicMessagesRequest) -> Response:
        canonical = body.to_canonical()
        if canonical.stream:
            started = perf_counter()
            events, metadata = await gateway.stream(canonical, _constraints(request))
            return StreamingResponse(
                _anthropic_stream(
                    _metered_events(request, canonical, metadata, events, started), metadata.model
                ),
                media_type="text/event-stream",
                headers=_route_headers(metadata),
            )
        started = perf_counter()
        response, metadata = await gateway.complete(canonical, _constraints(request))
        _meter(
            request,
            canonical,
            metadata,
            response.usage.input_tokens,
            response.usage.output_tokens,
            started,
        )
        return JSONResponse(anthropic_response(response), headers=_route_headers(metadata))

    @app.post("/v1/messages/count_tokens")
    async def count_tokens(body: AnthropicMessagesRequest) -> JSONResponse:
        canonical = body.to_canonical()
        characters = sum(
            len(part.text or "") for message in canonical.messages for part in message.content
        )
        return JSONResponse(
            {"input_tokens": max(1, math.ceil(characters / 4))},
            headers={"x-divine-token-count-approximate": "true"},
        )

    @app.get("/v1/models")
    async def models() -> dict[str, Any]:
        return {
            "object": "list",
            "data": [
                {"id": model.qualified_id, "object": "model", "owned_by": model.provider_id}
                for model in gateway.registry.all()
            ],
        }

    @app.get("/v1/divine/providers")
    async def providers() -> list[dict[str, Any]]:
        return [
            provider.model_dump(mode="json", exclude={"additional_headers"})
            for provider in config.providers
        ]

    @app.get("/v1/divine/providers/health")
    async def provider_health() -> list[dict[str, Any]]:
        return [
            {
                "provider_id": provider_id,
                "healthy": provider.health.healthy,
                "score": provider.health.score,
                "consecutive_failures": provider.health.consecutive_failures,
                "message": provider.health.message,
            }
            for provider_id, provider in gateway.providers.items()
        ]

    @app.get("/v1/divine/routes")
    async def routes() -> dict[str, Any]:
        return {"aliases": config.aliases, "fallback_chains": config.fallback_chains}

    @app.get("/v1/divine/usage")
    async def usage() -> list[dict[str, Any]]:
        if not database:
            return []
        return [
            {column.name: getattr(record, column.name) for column in UsageRecord.__table__.columns}
            for record in database.recent_usage()
        ]

    return app


def _constraints(request: Request) -> Any:
    from divine_router.api.controls import route_constraints

    return route_constraints(request)


def _error_response(request: Request, error: DivineError) -> JSONResponse:
    body = (
        error.anthropic_envelope()
        if request.url.path.startswith("/v1/messages")
        else error.openai_envelope()
    )
    return JSONResponse(body, status_code=error.status_code)


def _route_headers(metadata: RouteMetadata) -> dict[str, str]:
    return {
        "x-divine-provider": metadata.provider_id,
        "x-divine-model": metadata.model,
        "x-divine-route": metadata.route,
        "x-divine-fallback-count": str(metadata.fallback_count),
    }


async def _chat_stream(events: Any, model: str) -> AsyncIterator[str]:
    response_id = f"chatcmpl-{uuid4().hex}"
    saw_tools = False
    async for item in events:
        response_id = item.response_id
        if item.type == "content.delta":
            yield stream_chunk(response_id, model, item.delta)
        elif item.type in {"tool_call.start", "tool_call.delta"}:
            saw_tools = True
            yield stream_chunk(
                response_id,
                model,
                None,
                tool_call=item.item or {},
                tool_index=item.index,
            )
        elif item.type == "response.complete":
            yield stream_chunk(
                response_id,
                model,
                None,
                finish=True,
                finish_reason="tool_calls" if saw_tools else "stop",
            )
    yield "data: [DONE]\n\n"


def _request_id(candidate: str | None) -> str:
    if candidate and re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", candidate):
        return candidate
    return f"req_{uuid4().hex}"


async def _responses_stream(
    events: Any, model: str, request: ResponsesRequest
) -> AsyncIterator[str]:
    response_id = f"resp_{uuid4().hex}"
    message_id = f"msg_{uuid4().hex}"
    text = ""
    text_started = False
    text_output_index = 0
    next_output_index = 0
    tool_states: dict[int, dict[str, Any]] = {}
    completed_output: list[dict[str, Any]] = []
    created = {
        "id": response_id,
        "object": "response",
        "created_at": int(time()),
        "status": "in_progress",
        "model": model,
        "output": [],
        "error": None,
    }
    yield responses_event("response.created", {"response": created})
    yield responses_event("response.in_progress", {"response": created})
    async for item in events:
        if item.type == "content.delta":
            if not text_started:
                text_started = True
                text_output_index = next_output_index
                next_output_index += 1
                yield responses_event(
                    "response.output_item.added",
                    {
                        "output_index": text_output_index,
                        "item": {
                            "id": message_id,
                            "type": "message",
                            "status": "in_progress",
                            "role": "assistant",
                            "content": [],
                        },
                    },
                )
                yield responses_event(
                    "response.content_part.added",
                    {
                        "item_id": message_id,
                        "output_index": text_output_index,
                        "content_index": 0,
                        "part": {"type": "output_text", "text": "", "annotations": []},
                    },
                )
            text += item.delta or ""
            yield responses_event(
                "response.output_text.delta",
                {
                    "item_id": message_id,
                    "output_index": text_output_index,
                    "content_index": 0,
                    "delta": item.delta or "",
                },
            )
        elif item.type in {"tool_call.start", "tool_call.delta"}:
            incoming = item.item or {}
            state = tool_states.get(item.index)
            if state is None:
                state = {
                    "id": f"fc_{uuid4().hex}",
                    "call_id": incoming.get("id") or f"call_{uuid4().hex}",
                    "name": incoming.get("name") or "unknown_function",
                    "arguments": "",
                    "output_index": next_output_index,
                }
                tool_states[item.index] = state
                next_output_index += 1
                yield responses_event(
                    "response.output_item.added",
                    {
                        "output_index": state["output_index"],
                        "item": {
                            "id": state["id"],
                            "type": "function_call",
                            "status": "in_progress",
                            "call_id": state["call_id"],
                            "name": state["name"],
                            "arguments": "",
                        },
                    },
                )
            if incoming.get("name"):
                state["name"] = incoming["name"]
            argument_delta = str(incoming.get("arguments") or "")
            state["arguments"] += argument_delta
            if argument_delta:
                yield responses_event(
                    "response.function_call_arguments.delta",
                    {
                        "item_id": state["id"],
                        "output_index": state["output_index"],
                        "delta": argument_delta,
                    },
                )
    if text_started:
        part = {"type": "output_text", "text": text, "annotations": []}
        output_item = {
            "id": message_id,
            "type": "message",
            "status": "completed",
            "role": "assistant",
            "content": [part],
        }
        yield responses_event(
            "response.output_text.done",
            {
                "item_id": message_id,
                "output_index": text_output_index,
                "content_index": 0,
                "text": text,
            },
        )
        yield responses_event(
            "response.content_part.done",
            {
                "item_id": message_id,
                "output_index": text_output_index,
                "content_index": 0,
                "part": part,
            },
        )
        yield responses_event(
            "response.output_item.done",
            {"output_index": text_output_index, "item": output_item},
        )
        completed_output.append(output_item)
    for state in tool_states.values():
        output_item = {
            "id": state["id"],
            "type": "function_call",
            "status": "completed",
            "call_id": state["call_id"],
            "name": state["name"],
            "arguments": state["arguments"],
        }
        yield responses_event(
            "response.function_call_arguments.done",
            {
                "item_id": state["id"],
                "output_index": state["output_index"],
                "arguments": state["arguments"],
            },
        )
        yield responses_event(
            "response.output_item.done",
            {"output_index": state["output_index"], "item": output_item},
        )
        completed_output.append(output_item)
    completed = {
        **created,
        "id": response_id,
        "status": "completed",
        "output": completed_output,
        "output_text": text,
        "usage": None,
        "instructions": request.instructions,
    }
    yield responses_event("response.completed", {"response": completed})


async def _anthropic_stream(events: Any, model: str) -> AsyncIterator[str]:
    message_id = f"msg_{uuid4().hex}"
    text_index: int | None = None
    tool_indices: dict[int, int] = {}
    next_index = 0
    yield anthropic_event(
        "message_start",
        {
            "message": {
                "id": message_id,
                "type": "message",
                "role": "assistant",
                "model": model,
                "content": [],
                "stop_reason": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            }
        },
    )
    async for item in events:
        if item.type == "content.delta":
            if text_index is None:
                text_index = next_index
                next_index += 1
                yield anthropic_event(
                    "content_block_start",
                    {"index": text_index, "content_block": {"type": "text", "text": ""}},
                )
            yield anthropic_event(
                "content_block_delta",
                {
                    "index": text_index,
                    "delta": {"type": "text_delta", "text": item.delta or ""},
                },
            )
        elif item.type in {"tool_call.start", "tool_call.delta"}:
            incoming = item.item or {}
            output_index = tool_indices.get(item.index)
            if output_index is None:
                output_index = next_index
                next_index += 1
                tool_indices[item.index] = output_index
                yield anthropic_event(
                    "content_block_start",
                    {
                        "index": output_index,
                        "content_block": {
                            "type": "tool_use",
                            "id": incoming.get("id") or f"toolu_{uuid4().hex}",
                            "name": incoming.get("name") or "unknown_function",
                            "input": {},
                        },
                    },
                )
            arguments = str(incoming.get("arguments") or "")
            if arguments:
                yield anthropic_event(
                    "content_block_delta",
                    {
                        "index": output_index,
                        "delta": {"type": "input_json_delta", "partial_json": arguments},
                    },
                )
    for output_index in range(next_index):
        yield anthropic_event("content_block_stop", {"index": output_index})
    yield anthropic_event(
        "message_delta",
        {
            "delta": {"stop_reason": "tool_use" if tool_indices else "end_turn"},
            "usage": {"output_tokens": 0},
        },
    )
    yield anthropic_event("message_stop", {})


def _meter(
    request: Request,
    canonical: CanonicalRequest,
    metadata: RouteMetadata,
    input_tokens: int,
    output_tokens: int,
    started: float,
    time_to_first_token_ms: float | None = None,
) -> None:
    database: Database | None = request.app.state.database
    if not database:
        return
    database.add_usage(
        UsageRecord(
            request_id=request.state.request_id,
            client_type=request.headers.get("user-agent", "unknown")[:32],
            requested_model=canonical.model,
            selected_model=metadata.model,
            selected_provider=metadata.provider_id,
            route=metadata.route,
            fallback_attempts=metadata.fallback_count,
            status="success",
            latency_ms=(perf_counter() - started) * 1000,
            time_to_first_token_ms=time_to_first_token_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    )


async def _metered_events(
    request: Request,
    canonical: CanonicalRequest,
    metadata: RouteMetadata,
    events: Any,
    started: float,
) -> AsyncIterator[Any]:
    first_visible_ms: float | None = None
    input_tokens = 0
    output_tokens = 0
    completed = False
    async for item in events:
        if first_visible_ms is None and item.type in {
            "content.delta",
            "tool_call.start",
            "tool_call.delta",
        }:
            first_visible_ms = (perf_counter() - started) * 1000
        if item.usage:
            input_tokens = item.usage.get("input_tokens", input_tokens)
            output_tokens = item.usage.get("output_tokens", output_tokens)
        if item.type == "response.complete":
            completed = True
        yield item
    if completed:
        _meter(
            request,
            canonical,
            metadata,
            input_tokens,
            output_tokens,
            started,
            first_visible_ms,
        )
