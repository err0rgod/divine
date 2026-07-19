# Architecture

```text
Client protocol
→ Divine authentication and controls
→ protocol parser
→ canonical request
→ explicit resolver or automatic router
→ capability validation
→ retry/fallback executor and circuit breaker
→ provider-family adapter
→ canonical response or stream
→ client protocol serializer
```

## Boundaries

Protocol modules translate Chat Completions, Responses items/events, and Anthropic blocks. They do
not make provider HTTP calls. Canonical models preserve text, images, tools, tool results,
reasoning, usage, and stream lifecycle without binding the core to one vendor.

Provider families own authentication and upstream wire details. OpenAI-compatible services share
an adapter rather than duplicating clients per provider. The registry combines editable provider
configuration, discovered/manual model records, and conservative capabilities.

The router filters candidates before scoring. The executor owns deadlines, retry classification,
`Retry-After`, fallbacks, and stream commit boundaries. Provider health and circuit state feed back
into later route selection.

## Persistence and content

SQLite stores operational metadata and usage; credentials remain in keyring/environment/encrypted
storage. Prompt and response bodies are not persisted by default. Configuration is versioned TOML
with validation, atomic replacement, and backup.

This separation keeps new protocols, providers, and routing policies independently testable.
