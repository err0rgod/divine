# Quick start

## 1. Initialize

```console
divine doctor
divine providers
divine tui
```

All built-in provider templates begin disabled. In configuration, enable one provider, point its
credential reference at a keyring or environment variable, add a model (or use discovery), and
map `default` to `provider/model`.

## 2. Start

```console
divine serve
```

The default listener is `http://127.0.0.1:8742`. Put the generated local token in the client
environment as `DIVINE_API_TOKEN`; do not copy it into source code.

## 3. Verify

```console
curl http://127.0.0.1:8742/healthz \
  -H "Authorization: Bearer $DIVINE_API_TOKEN"
```

## 4. Make a request

```console
curl http://127.0.0.1:8742/v1/chat/completions \
  -H "Authorization: Bearer $DIVINE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"default","messages":[{"role":"user","content":"Reply with OK"}]}'
```

The response headers identify the chosen provider, model, route, fallback count, and request ID.
Use an explicit `provider/model` while validating a new setup.

## Background operation

```console
divine start
divine status
divine logs --lines 50
divine stop
```

Background lifecycle records a PID creation fingerprint and verifies command identity before
sending a stop signal, protecting unrelated processes from stale PID reuse.
