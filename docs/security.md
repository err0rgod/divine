# Security

Divine Router handles provider credentials and may receive sensitive prompts. Treat the process,
configuration directory, logs, and host account as a security boundary.

## Defaults

- An independent random Divine token protects every endpoint, including health on localhost.
- The listener binds to `127.0.0.1`; `0.0.0.0` requires explicit opt-in.
- CORS and prompt/response content logging are disabled.
- Request size, local rate, total deadline, and streaming idle timeout are bounded.
- SQLite records request metadata, usage, latency, and error categories—not credential values.

## Credential storage

Use an OS keyring when available. Environment references are suitable for managed processes.
Encrypted fallback uses authenticated encryption and requires a master password or master-key
environment variable. There is no custom cryptography.

Never commit `.env`, token files, encrypted credential material plus its master key, databases, or
logs. Configuration exports contain references but should still be reviewed before sharing.

## Redaction

Central redaction covers authorization headers, cookies, API/token-like fields, webhook URLs, and
query-string secrets. Exceptions and dry-run plans must pass through redaction. Redaction is a
backstop, not permission to log raw content.

## Network exposure

For multi-host use, place Divine Router behind a trusted TLS reverse proxy, restrict inbound IPs,
rotate the Divine token, and isolate the service account. Do not expose a raw loopback-oriented
development configuration to the internet.

See [self-hosting](self-hosting.md) for deployment controls.
