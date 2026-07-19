# One gateway. Explicit control.

<div class="hero" markdown>

Divine Router is a local-first AI API gateway for applications, experiments, and coding agents.
It presents OpenAI Chat Completions, OpenAI Responses, and Anthropic Messages interfaces while
keeping credentials, model selection, routing, and reliability under your control.

[Install Divine Router](installation.md){ .md-button .md-button--primary }
[Explore the API](api/chat-completions.md){ .md-button }

</div>

## What it does

- Select a provider and model explicitly with `provider/model` identifiers.
- Present aliases such as `coding`, `fast`, `reasoning`, `default`, and `auto`.
- Translate three client protocols through one canonical internal representation.
- Filter routes by tools, vision, structured output, context, tokens, health, cost, and policy.
- Apply bounded retries, fallback chains, circuit breakers, deadlines, and stream safety.
- Store operational metadata without storing prompts or provider credentials in SQLite.
- Run locally, in Docker, or behind a trusted self-hosted reverse proxy.

## API surface

| Client surface | Endpoint | Streaming | Tools |
|---|---|---:|---:|
| OpenAI Chat Completions | `POST /v1/chat/completions` | SSE | Yes |
| OpenAI Responses | `POST /v1/responses` | lifecycle SSE | Function tools |
| Anthropic Messages | `POST /v1/messages` | Anthropic events | Yes |
| Automatic routing | `POST /v1/auto/chat/completions` | SSE | Capability-filtered |

Administration includes health, readiness, models, routes, provider health, and usage endpoints.
All endpoints require the independent Divine token by default, including localhost.

## Deployment status

The [public documentation site](https://divine-router-docs-err0rgod.onrender.com/) is deployed from
the `feat/divine-router` branch. Public documentation deployment verified on 19 July 2026.

!!! warning "Compatibility is evidence-based"

    A provider template is not a live compatibility claim. Consult the
    [compatibility matrix](provider-compatibility.md) and build report before production use.

<p class="status-note">Documentation version 0.1 · Alpha development series</p>
