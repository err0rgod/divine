# Troubleshooting

## `401` from every endpoint

Use the independently generated Divine token, not a provider key. OpenAI clients send it as a
Bearer token; Anthropic clients may use `x-api-key`. Check isolated `DIVINE_CONFIG_DIR` values if
the CLI and server appear to use different tokens.

## Provider is disabled or unavailable

Run `divine doctor` and `divine providers`. Confirm the provider is enabled, its credential
reference names an available keyring/environment entry, and at least one model exists or discovery
succeeds. The doctor never prints the value.

## No route satisfies the request

Inspect `divine routes`, model capabilities, context/output limits, and deny/preference headers.
Tools, images, and structured output are not removed to force a route. Test with an explicit
qualified model to separate routing from provider behavior.

## Streaming stops without fallback

This is intentional after visible output. Retrying a partially emitted stream would duplicate
content. Use request IDs and provider health metadata to diagnose the upstream failure.

## Wrapper cannot find an agent

Confirm the underlying executable is on `PATH` and inspect its installed version/help. Use
`divine-AGENT --dry-run --model provider/model` to verify the isolated plan. Aider intentionally
fails when no verified installed flow exists.

## Server PID is reported stale

Divine Router validates PID, creation time, and command identity. A stale or manually edited PID
record is removed or reported stopped rather than signaling an unrelated process.

## Docker is unreachable

The in-container config must explicitly bind `0.0.0.0`, while the host port should remain bound to
`127.0.0.1` unless a protected remote deployment is intended. Retrieve the generated Divine token
from the persistent config volume through an operator-controlled secure method.
