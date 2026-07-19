# Coding-agent integrations

Divine Router provides isolated wrappers for supported coding agents. Every wrapper selects an
explicit model or alias; `auto` is rejected because coding-agent traffic must not change models
unpredictably during a task.

The wrappers forward unrecognized arguments verbatim, preserve the child process exit code,
forward termination signals, and remove temporary configuration on exit. They never modify the
operator's normal agent configuration. Use `--no-start` when the router is managed separately.

## Shared options

```console
divine-codex --model openai/gpt-example exec "Inspect this repository"
divine-claude --profile work -p "Explain the failing test"
divine-opencode --dry-run --model groq/model-name run "Review this patch"
```

- `--model PROVIDER/MODEL` selects an explicit model or configured alias.
- `--profile NAME` reads a model from `[cli_profiles.NAME]` in Divine configuration.
- `--dry-run` prints a credential-redacted launch plan without starting anything.
- `--no-start` skips the authenticated health check and automatic local server startup.

The environment variables `DIVINE_CODEX_MODEL`, `DIVINE_CLAUDE_MODEL`, and
`DIVINE_OPENCODE_MODEL` can provide per-agent defaults. The fallback default is the explicit
`coding` alias. Configure that alias before first use.

## Codex CLI

`divine-codex` creates a temporary `CODEX_HOME` containing a custom model provider with:

```toml
base_url = "http://127.0.0.1:8742/v1"
env_key = "DIVINE_API_TOKEN"
wire_api = "responses"
```

The wrapper passes `--strict-config` and routes Codex through Divine Router's `/v1/responses`
implementation. The Divine token is supplied only through the child environment. The installed
Codex CLI version inspected during this build is recorded in `BUILD_REPORT.md`.

## Claude Code

`divine-claude` creates a temporary Claude configuration directory and sets the documented
gateway variables `ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN`. It passes the selected model
explicitly and does not replace the operator's Claude login or settings.

## OpenCode

`divine-opencode` creates a temporary OpenCode custom-provider configuration using
`@ai-sdk/openai-compatible`, points it at Divine Router's `/v1` API, disables sharing and
automatic updates for the isolated run, and supplies the Divine token through an environment
reference.

## Aider

The `divine-aider` entry point is packaged for consistent discovery, but it fails clearly when a
supported Aider installation and reliable isolated base-URL flow are unavailable. Aider was not
installed in the build environment, so no compatibility claim is made.

## Verification status

Fake-executable tests cover configuration isolation, argument forwarding (including spaces),
redaction, exit-code preservation, missing executables, and generated Codex/Claude/OpenCode
configuration. Real end-to-end agent tests require an enabled explicit provider/model and are
reported separately; unit tests are not presented as live compatibility proof.
