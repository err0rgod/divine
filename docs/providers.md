# Provider setup

Provider templates describe transport; they do not hardcode permanent model lists. Use discovery
where supported and manual models where it is not.

Each provider defines an ID, adapter family, base URL, credential reference, auth style, headers,
discovery path, timeout, enabled state, capability overrides, retry policy, trust level, and
verification status.

## Adapter families

| Family | Use |
|---|---|
| `openai-compatible` | OpenAI and compatible direct providers/gateways |
| `anthropic` | Native Anthropic Messages transport |
| `gemini` | Native Google Gemini transport |
| `bedrock-extension` | Extension boundary; initial adapter not complete |
| `vertex-extension` | Extension boundary; initial adapter not complete |

Use a generic custom template when a service documents the relevant compatibility contract. Do
not guess paths: provider APIs sometimes put `/v1` in the configured base URL and sometimes in
the operation path.

## Discovery and manual models

```console
divine test-provider PROVIDER
divine models
```

Discovery is a read-only credentialed request. A provider without discovery can list `models` in
TOML. Apply capability overrides when documentation or testing supports them:

```toml
[providers.capabilities]
streaming = true
tools = true
structured_output = false
vision = false
context_window = 131072
max_output_tokens = 8192
```

Overclaiming a capability is dangerous: it permits dispatch of a request the upstream might
silently degrade. Start conservatively and test tools, images, structured output, and streams.

## Verification labels

- `verified-live`: a successful live request was recorded for this build.
- `verified-mocked`: adapter behavior has mocked integration coverage.
- `compatible-unverified`: official documentation supports the template, without a live request.
- `experimental`: incomplete or uncertain compatibility.
- `disabled`: intentionally unavailable.

See the [compatibility matrix](provider-compatibility.md).
