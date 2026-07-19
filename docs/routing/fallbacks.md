# Fallback chains

Fallback chains are ordered provider/model alternatives used after a retryable pre-stream failure.

```toml
[fallback_chains]
"openai/model-a" = ["anthropic/model-b", "groq/model-c"]
```

Before attempting a fallback, Divine Router applies the same capability and policy validation as
the primary route. It will not fall back from a tool-capable request to a model without tools.

Retryable categories include transient network failures, bounded timeouts, rate limits, and
selected upstream 5xx responses. Authentication, malformed requests, unsupported capabilities,
and deterministic upstream errors are not blindly retried. `Retry-After` is honored within the
total request deadline.

!!! danger "Stream boundary"

    A stream may retry or fall back only before visible output begins. After the first client
    event, the failure is surfaced on that stream; restarting elsewhere would duplicate content.

Circuit breakers exclude repeatedly failing routes until a recovery probe. Provider health scores
incorporate recent success, latency, and circuit state.
