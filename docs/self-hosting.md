# Self-hosting

## Local service

`divine serve` is the simplest foreground deployment. `divine start` adds a per-user background
process with logs and fingerprinted lifecycle control. A systemd user-service example is provided
under `examples/systemd/`.

On Windows, use a normal user account and a user-scoped startup task that invokes `divine serve`.
Point `DIVINE_CONFIG_DIR`, `DIVINE_DATA_DIR`, and `DIVINE_LOG_DIR` at user-writable locations; do
not require Administrator privileges.

## Docker

```console
docker compose up --build
```

The image uses a non-root runtime user and the Compose example drops Linux capabilities, enables
`no-new-privileges`, persists local metadata, and publishes only on host loopback. The mounted
example config explicitly allows `0.0.0.0` inside the container because container loopback would
not reach the host port mapping.

Persist the configuration/token and data paths. Inject provider credential environment variables
at runtime; never add `.env` to the image context.

## Reverse proxy checklist

- TLS termination and strict inbound firewall rules.
- Preserve SSE buffering/flush behavior and long-lived connection timeouts.
- Keep Divine authentication enabled.
- Set request-body limits at both proxy and application layers.
- Disable proxy access logs containing authorization or query-string secrets.
- Back up configuration and metadata without exporting keyring secrets.

Render deployment in this repository is for the static documentation site only, not the gateway.
