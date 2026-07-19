# OpenAI Responses API

`POST /v1/responses` implements the Responses wire protocol used by current Codex CLI custom
providers. It has explicit converters for input items, output messages, function calls,
function-call outputs, usage, request IDs, and streaming lifecycle events.

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8742/v1", api_key=divine_token)
response = client.responses.create(
    model="provider/model",
    instructions="Be concise.",
    input="Explain circuit breakers in one sentence.",
)
print(response.output_text)
```

## Function-call round trip

Input can contain typed items:

```json
{
  "model": "provider/tool-model",
  "input": [
    {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Check 42"}]},
    {"type": "function_call_output", "call_id": "call_1", "output": "valid"}
  ],
  "tools": [
    {"type": "function", "name": "check", "description": "Validate a value", "parameters": {"type": "object"}}
  ]
}
```

Function calls are returned as output items instead of being flattened into assistant text.
Reasoning-related fields are preserved when representable by the selected model and adapter.

## Streaming lifecycle

With `stream: true`, Divine Router emits Responses-style lifecycle events, including creation,
output item/content deltas, completion, and failure events. It does not redirect the request to
Chat Completions at the HTTP layer.

Hosted tools, stateful conversation features, and unsupported fields return clear compatibility
errors. They are not silently ignored.
