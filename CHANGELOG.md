# Changelog

All notable changes are documented here. Divine Router follows semantic versioning after the
initial development series.

## [Unreleased]

### Added

- Unified OpenAI Chat Completions, OpenAI Responses, and Anthropic Messages API surfaces.
- Provider-neutral canonical request, response, tool-call, and streaming models.
- OpenAI-compatible, Anthropic, and Gemini adapter families with editable provider templates.
- Explicit aliases, deterministic automatic routing, capability validation, retries, fallbacks,
  circuit breakers, health scoring, and metadata-only usage tracking.
- Authenticated administrative API, local rate limiting, redaction, keyring/environment/encrypted
  credential resolution, atomic TOML configuration, CLI, and operations TUI.
- Isolated wrappers for installed Claude Code, Codex CLI, and OpenCode agents.
- Mocked integration and official OpenAI/Anthropic SDK compatibility tests.

### Security

- Authentication is required by default, including on localhost.
- Remote binding requires explicit configuration; CORS and content logging are disabled by
  default.

## [0.1.0] - Unreleased

Initial development release.
