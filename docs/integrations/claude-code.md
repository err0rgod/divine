# Claude Code integration

`divine-claude` routes an installed Claude Code CLI to Divine Router's Anthropic-compatible API.
It creates a temporary `CLAUDE_CONFIG_DIR`, passes a temporary settings file, and sets the
documented gateway variables `ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN` only in the child
environment.

```console
divine-claude --model anthropic/model-name -p \
  "Reply with exactly DIVINE_CLAUDE_OK and nothing else."
```

The wrapper does not overwrite the normal Claude login or settings. It forwards remaining
arguments, signals, and exit status. Use `--dry-run` for a redacted plan.

Automatic routing is rejected. Live verification requires an explicit enabled model and a tiny
non-interactive prompt; mocked wrapper tests alone are not a provider or Claude Code live claim.
