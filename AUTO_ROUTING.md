# Automatic Routing

Automatic routing is available through `POST /v1/auto/chat/completions` or by requesting model
`auto` on the normal Chat Completions endpoint.

Stage 1 filters models deterministically for enabled state, provider health, credentials,
allowlists/denylists, streaming, tools, vision, structured output, output-token limits, and cost.
Stage 2 applies a local rule-based task classifier and scores the remaining models. Supported
classes include simple chat, extraction, summarization, coding, debugging, agentic tools,
mathematical/deep reasoning, long context, creative writing, vision, low latency, and low cost.

Routing controls are validated headers:

- `x-divine-max-cost`
- `x-divine-prefer: cost|latency|quality`
- `x-divine-deny-provider`
- `x-divine-disable-fallback`
- `x-divine-disable-classifier`

Responses identify the chosen provider, model, route, fallback count, and request ID. Coding-agent
wrappers use explicit models and never automatic routing by default.

An optional LLM classifier is represented in configuration but disabled by default. A later
milestone will add its bounded implementation; until then all classification remains local and
no prompt sample is sent to a second provider.
