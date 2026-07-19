# OpenAI Chat Completions

`POST /v1/chat/completions` accepts OpenAI-style chat requests. `POST
/v1/auto/chat/completions` forces automatic routing; setting `model` to `auto` has the same routing
effect on the normal endpoint.

Supported request fields include `model`, `messages`, `temperature`, `top_p`, `max_tokens`,
`max_completion_tokens`, `stop`, `stream`, `tools`, `tool_choice`, `response_format`, and `seed`.
Unsupported or invalid fields return an OpenAI-compatible error envelope.

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8742/v1", api_key=divine_token)
completion = client.chat.completions.create(
    model="provider/model",
    messages=[{"role": "user", "content": "Give one word for reliable."}],
    temperature=0,
    max_tokens=16,
)
print(completion.choices[0].message.content)
```

## Streaming

```python
stream = client.chat.completions.create(
    model="provider/model",
    messages=[{"role": "user", "content": "Count to three."}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")
```

The HTTP response uses `text/event-stream` and ends with `[DONE]`. Once any upstream content has
been emitted, Divine Router will not retry or switch providers, preventing duplicated text.

## Function tools

```python
completion = client.chat.completions.create(
    model="provider/tool-model",
    messages=[{"role": "user", "content": "Weather in Pune?"}],
    tools=[{
        "type": "function",
        "function": {
            "name": "weather",
            "description": "Get current weather",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    }],
)
```

Tools, images, and structured-output requirements are capability-validated and never silently
removed.
