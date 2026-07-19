# Configuration

Divine Router uses validated, versioned TOML. Writes are atomic and an existing file is backed up
before replacement.

```toml
schema_version = 1
usage_retention_days = 90

[server]
host = "127.0.0.1"
port = 8742
allow_remote_bind = false
rate_limit_per_minute = 120
request_body_limit_bytes = 10485760
total_deadline_seconds = 120.0
streaming_idle_timeout_seconds = 45.0

[aliases]
default = ["openai/example-model"]
coding = ["openai/example-model"]

[logging]
level = "INFO"
content_logging = false

[[providers]]
id = "openai"
display_name = "OpenAI"
adapter = "openai-compatible"
base_url = "https://api.openai.com/v1"
enabled = true
models = ["example-model"]
verification = "compatible-unverified"

[providers.credential]
environment = "OPENAI_API_KEY"
```

Base URLs are editable. Local HTTP is accepted only for loopback hosts; external providers require
HTTPS. Unknown fields and duplicate provider IDs fail validation.

## Credential priority

1. Operating-system keyring.
2. Environment-variable reference.
3. Authenticated encrypted file, requiring a master password or key environment variable.

Credential values are never stored in SQLite or exported by `divine config export`. Use
`divine config import FILE` for validated atomic replacement. Missing credentials disable the
affected provider without breaking startup or normal tests.

## Remote binding

`host = "0.0.0.0"` is rejected unless `allow_remote_bind = true`. That switch is an explicit
acknowledgement, not network protection; see [self-hosting](self-hosting.md).
