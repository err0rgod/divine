# Architecture

Divine Router separates wire protocols, canonical models, routing, reliability, and provider
transport. Protocol modules never issue provider HTTP requests, and provider adapters never
serialize client-facing responses.

```text
Client protocol
  -> Divine authentication and request limits
  -> protocol parser
  -> canonical request
  -> explicit resolver or automatic router
  -> capability validation
  -> retry/fallback executor and circuit breaker
  -> provider-family adapter
  -> canonical response or stream events
  -> protocol serializer
```

The three implemented adapter families are `OpenAICompatibleProvider`, `AnthropicProvider`, and
`GeminiProvider`. Abstract extension interfaces reserve Bedrock and Vertex integration for
optional packages that can supply their platform authentication safely.

The canonical layer represents text, images, tool calls, tool results, generation controls,
usage, and typed stream events. OpenAI Responses items have their own explicit converter; the
Responses endpoint is not a redirect to Chat Completions.

SQLite stores request metadata and token/cost fields, never provider credentials or prompt
content. Configuration uses validated TOML with schema versioning, atomic replacement, and a
backup before overwrite.
