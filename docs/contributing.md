# Contributing

Install test and documentation dependencies in a virtual environment:

```console
python -m pip install -e ".[test,docs]"
ruff format --check src tests migrations
ruff check src tests migrations
mypy src/divine_router
pytest
python -m build
mkdocs build --strict
```

Keep protocol conversion, canonical models, routing, and provider transports separated. Add
mocked failure/stream/tool coverage for behavior changes and update user documentation in the same
milestone.

Credentialed live tests must be opt-in with `DIVINE_LIVE_TESTS=1`, tiny, timeout-bounded, and
redacted. Never promote a provider to `verified-live` without recorded evidence.

Use conventional commits and review staged files for secrets. See the repository
`CONTRIBUTING.md` for the complete policy and `SECURITY.md` for private vulnerability reporting.
