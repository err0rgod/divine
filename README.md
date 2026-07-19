# Divine Router

Divine Router is a local-first, self-hostable AI API gateway. It exposes OpenAI Chat
Completions, OpenAI Responses, Anthropic Messages, and policy-driven automatic routing while
keeping protocol translation separate from provider-specific transport code.

The request flow is:

```text
client protocol -> Divine authentication -> canonical request -> model resolution/routing
-> capability validation -> retry/fallback executor -> provider adapter -> client protocol
```

The current implementation includes OpenAI-compatible, Anthropic, and Gemini adapter families;
streaming lifecycle conversion; function tools; model capability filtering; retries, fallbacks,
circuit breakers; metadata-only usage persistence; and an editable provider template catalogue.

All endpoints require the independent Divine API token by default, including localhost:

```text
POST /v1/chat/completions
POST /v1/responses
POST /v1/messages
POST /v1/auto/chat/completions
GET  /v1/models
GET  /v1/divine/providers
GET  /v1/divine/providers/health
GET  /v1/divine/usage
GET  /v1/divine/routes
```

Unsupported Responses hosted tools and stateful fields return explicit compatibility errors.
Divine Router never silently removes tools, images, or structured-output requirements.

The project is under active construction. See `BUILD_REPORT.md` for verified status; no
compatibility claim is considered complete until its corresponding automated or live check is
recorded there.
