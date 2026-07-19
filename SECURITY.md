# Security

Divine Router is authenticated by default, including on loopback interfaces. The server binds to
`127.0.0.1` by default and refuses `0.0.0.0` unless `allow_remote_bind` is explicitly enabled.

Provider credentials are resolved in this priority order:

1. operating-system keyring;
2. environment-variable reference;
3. Fernet-authenticated encrypted file with `DIVINE_MASTER_KEY`.

Credentials are never stored in SQLite. Central redaction covers authorization headers, API
keys, cookies, known token formats, sensitive mappings, and secret query parameters. Prompt and
response bodies are not logged by default.

Additional defaults include request-body limits, local rate limiting, constant-time token
comparison, disabled CORS, provider-specific timeouts, and explicit remote-bind opt-in. Do not
expose the server directly to an untrusted network without TLS and an external reverse proxy.

Report suspected vulnerabilities privately to the repository owner. Do not include real API
keys, prompts, or customer data in an issue.
