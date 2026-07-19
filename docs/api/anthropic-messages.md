# Anthropic Messages

`POST /v1/messages` accepts native Anthropic-style messages. Authenticate with `x-api-key` or
`Authorization: Bearer`; `anthropic-version` is recognized.

```python
from anthropic import Anthropic

client = Anthropic(base_url="http://127.0.0.1:8742", api_key=divine_token)
message = client.messages.create(
    model="provider/model",
    system="Be concise.",
    max_tokens=64,
    messages=[{"role": "user", "content": "Explain retries."}],
)
print(message.content[0].text)
```

Supported content includes text, supported image blocks, tool use, and tool result blocks. Request
controls include `max_tokens`, `temperature`, `top_p`, `top_k`, `stop_sequences`, `tools`, and
`tool_choice`.

## Streaming

```python
with client.messages.stream(
    model="provider/model",
    max_tokens=64,
    messages=[{"role": "user", "content": "Count to three."}],
) as stream:
    for text in stream.text_stream:
        print(text, end="")
```

Events follow the Anthropic message/content lifecycle and include usage when available.

## Token counting

`POST /v1/messages/count_tokens` provides a practical local estimate when exact provider-native
counting is unavailable. Treat an estimate conservatively for context-limit enforcement.
