# Contributing to Divine Router

Divine Router is protocol infrastructure. Changes must preserve the separation between client
protocol conversion, canonical models, routing, and provider transport. Provider-specific
conditions belong in adapters or configuration templates, not API handlers.

## Development setup

```console
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[test,docs]"  # Windows
python -m pip install -e ".[test,docs]"               # POSIX venv
```

Run the gates before opening a pull request:

```console
ruff format --check src tests migrations
ruff check src tests migrations
mypy src/divine_router
pytest
python -m build
mkdocs build --strict
```

Tests must not require credentials unless marked `live` and guarded by `DIVINE_LIVE_TESTS=1`.
Never put keys in fixtures. Prefer `respx`, the canonical fake provider, and official SDK clients
pointed at the in-process ASGI application.

Use conventional commit messages. Update public documentation in the same milestone as behavior.
Do not claim a provider is `verified-live` without a successful live request recorded in
`BUILD_REPORT.md` and `PROVIDER_COMPATIBILITY.md`.

## Security reports

Do not open a public issue for a suspected credential exposure or authentication bypass. Follow
the private reporting guidance in `SECURITY.md`.
