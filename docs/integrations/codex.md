# Codex CLI integration

`divine-codex` creates a temporary `CODEX_HOME/config.toml` with a custom provider:

```toml
model_provider = "divine"

[model_providers.divine]
name = "Divine Router"
base_url = "http://127.0.0.1:8742/v1"
env_key = "DIVINE_API_TOKEN"
wire_api = "responses"
```

It invokes Codex with strict isolated configuration and an explicit model:

```console
divine-codex --model provider/model exec \
  "Create result.txt containing DIVINE_CODEX_OK"
```

The token remains in the child environment, the profile is deleted on exit, and the user's normal
Codex configuration is not edited. This integration exercises Divine Router's `/v1/responses`
converter; it does not route Codex through Chat Completions.

Use a temporary working directory and a strict timeout for real smoke tests.
