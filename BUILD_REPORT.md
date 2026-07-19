# Divine Router Build Report

This report is maintained during implementation. A final verification matrix will replace
provisional entries only after the corresponding checks have run.

## Preflight (2026-07-19)

- Repository: `D:\divine`
- Branch: `feat/divine-router`
- Remote: `https://github.com/err0rgod/divine.git`
- Starting commit: `3e1670e`
- Python: 3.13.12 selected; Python 3.14 is also installed
- Shell/OS: PowerShell on Windows
- GitHub CLI: 2.92.0; authentication invalid, so pushes and CI inspection are blocked
- Render CLI: 2.21.0; authenticated; no existing Divine Router documentation static site found
- Docker: client 29.5.3 installed; daemon unavailable during preflight
- Installed coding agents: Codex CLI 0.144.4, Claude Code 2.1.211, OpenCode 1.18.3
- Unavailable coding agents: Aider
- Sensitive files: `.env` is ignored; only variable names were inspected
- Render executable: preserved locally and removed from Git tracking

## Current status

- Foundation: configuration, canonical models, redaction, credential resolution, and SQLite
  usage persistence implemented
- Foundation checks: Ruff format passed, Ruff lint passed, strict mypy passed, 7 tests passed
- Core gateway: all required API routes implemented with provider-neutral conversions
- Provider families: OpenAI-compatible, Anthropic, and Gemini implemented; Bedrock and Vertex
  extension interfaces defined
- Routing/reliability: explicit aliases, automatic filtering/scoring, retries, fallbacks, circuit
  breakers, provider health, and routing metadata implemented
- Core checks: Ruff and strict mypy pass; 41 tests pass (mocked, no live-provider claim)
- Core coverage: 90.96% across protocol, routing, and reliability modules (85% gate passed)
- SDK smoke tests: official OpenAI and Anthropic Python SDKs pass non-streaming, streaming,
  tool-call, and representative Responses requests against the local ASGI application
- Operations surface: Typer lifecycle/configuration commands and the keyboard-first Textual TUI
  are implemented; background process control validates PID creation fingerprints and command
  identity before sending signals
- Coding-agent wrappers: isolated Claude Code, Codex Responses, and OpenCode profiles implemented;
  automatic routing is rejected and Aider reports unavailable in this environment
- Wrapper/operations verification: generated-profile, argument-forwarding, spaces-in-paths,
  redaction, child-exit-code, CLI initialization/export, stale-PID, and TUI navigation tests pass
- Current local suite: 60 tests passed plus 1 credential-gated live test skipped by default; Ruff
  and strict mypy pass (mocked, no live-provider claim)
- Provider live tests: Groq and DeepSeek each reached official model discovery once and returned
  HTTP 401; credentials marked unavailable and not retried; all other keys intentionally untested
- Real coding-agent end-to-end tests: blocked because no tested compatible provider credential is
  valid; fake-agent coverage is not treated as live proof
- Persistence migration: Alembic upgrade to revision `0001` and downgrade to base both passed
- Documentation: MkDocs Material site created; `mkdocs build --strict` passes
- Packaging: wheel and source distribution built; wheel plus dependencies installed in a clean
  Python 3.13 environment; package import and installed `divine --help` passed
- Server smoke: real isolated background start, authenticated health/status, and stop passed
- Render Blueprint: authenticated CLI validation passed (`valid: true`, one static-site action)
- Docker: Dockerfile and Compose configuration created; build remains unverified because the
  installed Docker Desktop daemon is not running
- GitHub CI: blocked by invalid GitHub CLI authentication
- Render deployment: blocked until commits can be pushed to the private GitHub repository; no
  service was created from stale remote source
