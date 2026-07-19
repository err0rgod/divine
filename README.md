# Divine Router

Divine Router is a local-first, self-hostable AI API gateway. It exposes OpenAI Chat
Completions, OpenAI Responses, Anthropic Messages, and policy-driven automatic routing while
keeping protocol conversion separate from provider-specific transport. It is infrastructure,
not a chat application.

[Documentation](https://divine-router-docs-err0rgod.onrender.com/) |
[Installation](https://divine-router-docs-err0rgod.onrender.com/installation/) |
[Quick start](https://divine-router-docs-err0rgod.onrender.com/quick-start/) |
[API guides](https://divine-router-docs-err0rgod.onrender.com/api/chat-completions/) |
[Provider compatibility](https://divine-router-docs-err0rgod.onrender.com/provider-compatibility/) |
[Security](https://divine-router-docs-err0rgod.onrender.com/security/)

> **Development status:** the package is an alpha. Mocked and SDK compatibility are tested;
> provider live status is reported separately and never inferred from a template.

## Why Divine Router

- Use one local endpoint for OpenAI-compatible, Anthropic-compatible, and automatic-routing
  clients.
- Keep provider credentials local and outside the usage database.
- Select `provider/model` explicitly or route through configurable aliases and policies.
- Validate tool, vision, structured-output, context, and token requirements before dispatch.
- Apply bounded retries, fallbacks, circuit breakers, request deadlines, and stream safety.
- Integrate installed Codex, Claude Code, and OpenCode CLIs through isolated temporary profiles.
- Inspect provider health, routes, usage, latency, and redacted logs from the CLI or TUI.

## Supported API surfaces

| Surface | Endpoint | Streaming | Tool calls |
|---|---|---:|---:|
| OpenAI Chat Completions | `POST /v1/chat/completions` | SSE | Yes |
| OpenAI Responses | `POST /v1/responses` | Lifecycle SSE | Function tools |
| Anthropic Messages | `POST /v1/messages` | Anthropic events | Yes |
| Automatic routing | `POST /v1/auto/chat/completions` | SSE | Capability-filtered |

Administrative endpoints expose authenticated health, readiness, model, provider, route, and
usage information. Authentication is required by default, including on localhost.

## Architecture

```text
client protocol -> Divine authentication -> canonical request -> model resolution/routing
-> capability validation -> retry/fallback executor -> provider adapter -> client protocol
```

OpenAI-compatible providers share one adapter family. Anthropic and Gemini have dedicated
families, while Bedrock and Vertex expose extension boundaries. The router validates tools,
images, structured output, context, and output-token requirements before dispatch and will not
silently discard unsupported features.

## Install

Python 3.12 or newer is required.

```console
git clone https://github.com/err0rgod/divine.git
cd divine
python -m venv .venv
# Windows: .venv\Scripts\activate
# POSIX:   . .venv/bin/activate
python -m pip install -e .
```

For development and documentation:

```console
python -m pip install -e ".[test,docs]"
```

## Quick start

Initialize a platform-appropriate configuration and independent Divine API token:

```console
divine doctor
divine providers
divine tui
```

Edit `config.toml` through the TUI or export/import commands. Enable only providers whose
credential references exist, configure at least one model, and map `default` or another alias to
qualified `provider/model` identifiers. Then run:

```console
divine serve
```

The default listener is `127.0.0.1:8742`. Authentication is required even on localhost. Retrieve
the locally generated token from the platform configuration directory and put it in a client
environment variable; never paste it into source control.

For the complete provider and alias setup, follow the
[hosted quick-start guide](https://divine-router-docs-err0rgod.onrender.com/quick-start/).

## API examples

```console
curl http://127.0.0.1:8742/v1/chat/completions \
  -H "Authorization: Bearer $DIVINE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"provider/model","messages":[{"role":"user","content":"Hello"}]}'
```

```python
import os

from openai import OpenAI

divine_token = os.environ["DIVINE_API_TOKEN"]
client = OpenAI(base_url="http://127.0.0.1:8742/v1", api_key=divine_token)
reply = client.chat.completions.create(
    model="provider/model",
    messages=[{"role": "user", "content": "Hello"}],
)
print(reply.choices[0].message.content)

response = client.responses.create(model="provider/model", input="Summarize this text")
print(response.output_text)
```

```python
import os

from anthropic import Anthropic

divine_token = os.environ["DIVINE_API_TOKEN"]
client = Anthropic(base_url="http://127.0.0.1:8742", api_key=divine_token)
message = client.messages.create(
    model="provider/model",
    max_tokens=128,
    messages=[{"role": "user", "content": "Hello"}],
)
print(message.content[0].text)
```

Streaming, function tools, routing-control headers, and protocol-specific errors are covered in
the [API documentation](https://divine-router-docs-err0rgod.onrender.com/api/chat-completions/).

## Documentation

The complete guide is published at
[divine-router-docs-err0rgod.onrender.com](https://divine-router-docs-err0rgod.onrender.com/).
It covers configuration, every supported API surface, routing, fallbacks, the CLI and TUI,
coding-agent integration, security, architecture, self-hosting, and troubleshooting. The same
source is available in [`docs/`](docs/), and strict local validation is available with:

```console
python -m pip install -e ".[docs]"
mkdocs build --strict
```

## Operations

`divine` opens the keyboard-first operations TUI. Commands include `serve`, `start`, `stop`,
`restart`, `status`, `doctor`, `providers`, `models`, `routes`, `logs`, `test-provider`, and
validated `config export/import`. The TUI manages configuration and status; it intentionally has
no chat screen.

Installed coding agents can be routed through explicit models without changing their normal
configuration:

```console
divine-codex --model provider/model exec "Inspect the tests"
divine-claude --model provider/model -p "Explain this function"
divine-opencode --model provider/model run "Review the diff"
```

Use `--dry-run` to inspect a redacted plan. Wrappers reject `auto`; see
`CLI_INTEGRATIONS.md` for isolation guarantees and current verification status.

## Provider configuration

The built-in catalogue contains editable templates for direct providers, local servers, and
gateways. All templates start disabled. Credentials are referenced by keyring name, environment
variable, or authenticated encrypted-file entry and are never stored in SQLite. Model discovery
is used where supported; manual models and capability overrides remain available.

See [`PROVIDER_COMPATIBILITY.md`](PROVIDER_COMPATIBILITY.md) or the
[published compatibility matrix](https://divine-router-docs-err0rgod.onrender.com/provider-compatibility/)
before relying on a provider. A template is not a live test.

## Security

- Keep the generated Divine token and provider credentials out of Git and logs.
- Remote `0.0.0.0` binding requires `allow_remote_bind = true`; add a firewall or trusted reverse
  proxy before exposing it.
- CORS and content logging are disabled by default.
- Metadata is recorded by default, not prompt/response content.
- Configuration imports are validated and written atomically with a backup.

Read [`SECURITY.md`](SECURITY.md) before self-hosting beyond a single-user workstation.

## Tests and quality gates

```console
ruff format --check src tests migrations
ruff check src tests migrations
mypy src/divine_router
pytest
pytest --cov=divine_router.protocols --cov=divine_router.routing \
  --cov=divine_router.reliability --cov-report=term-missing
python -m build
mkdocs build --strict
```

Optional live tests require both `DIVINE_LIVE_TESTS=1` and an explicitly enabled provider. Missing
credentials never fail the normal suite.

## Docker

The image runs as a non-root user. The example Compose configuration explicitly opts into the
container-required `0.0.0.0` bind but publishes it only on host loopback:

```console
docker compose up --build
```

Use a persistent volume for configuration/token and metadata. Do not bake `.env` or keys into an
image.

## Limitations

- Compatibility is a meaningful subset, not a promise that every vendor extension is portable.
- Hosted Responses tools and stateful features return explicit compatibility errors.
- A stream is never retried or failed over after visible output begins.
- Pricing is editable and date-stamped; it is not guaranteed current.
- Bedrock and Vertex are extension interfaces, not complete initial adapters.
- Aider integration is unavailable unless a supported installed version provides a reliable
  isolated base-URL flow.

See [`BUILD_REPORT.md`](BUILD_REPORT.md) for what was actually executed in this build. Development
and review guidance is in [`CONTRIBUTING.md`](CONTRIBUTING.md), and the complete user guide is on
the [documentation site](https://divine-router-docs-err0rgod.onrender.com/).
