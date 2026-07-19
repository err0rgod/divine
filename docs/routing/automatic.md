# Automatic routing

Automatic routing is for ordinary application requests and experiments. Coding-agent wrappers
use explicit models by default.

Use either:

```text
POST /v1/auto/chat/completions
```

or `"model": "auto"` on `/v1/chat/completions`.

## Stage 1: deterministic filtering

Candidates must satisfy enabled/credential state, circuit and provider health, context and output
limits, tools, vision, structured output, budget, allowlists, denylists, and request preferences.
An empty candidate set is an error; requirements are not stripped to make a route fit.

## Stage 2: classification and scoring

The built-in rules identify simple chat, extraction, summarization, coding, debugging, agentic
tools, mathematical/deep reasoning, long context, creative writing, vision, low latency, and low
cost. Scores combine task fit with health, latency, cost, and policy preferences.

An optional LLM classifier can use a configured Groq provider/model. It uses bounded sampled
content, strict JSON, a short timeout, and a small output budget; failures fall back to rules.
Enable it only after considering that classification sends content to another provider.

## Request controls

| Header | Meaning |
|---|---|
| `x-divine-max-cost` | Maximum accepted configured request cost |
| `x-divine-prefer` | `latency`, `cost`, `quality`, or supported preference |
| `x-divine-deny-provider` | Comma-separated provider IDs to exclude |
| `x-divine-disable-fallback` | Disable fallback for this request |
| `x-divine-disable-classifier` | Use deterministic routing only |

Invalid values are rejected. Responses include `x-divine-provider`, `x-divine-model`,
`x-divine-route`, `x-divine-fallback-count`, and `x-divine-request-id`.
