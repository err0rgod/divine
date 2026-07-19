You are the lead engineer responsible for independently designing, implementing, testing, documenting, deploying and delivering a production-quality project called **Divine Router**.

The operator may be asleep and unavailable. Work autonomously until the project is in the strongest complete state possible.

# Operating rules

At the beginning:

1. Inspect the current directory, operating system, shell, installed Python versions, Git state, GitHub CLI authentication, Render CLI authentication, available coding CLI agents and existing project files.
2. Print one consolidated section called `Initial Questions and Assumptions`.
3. List questions that would normally matter, but do not wait for answers.
4. For every question, state the safe default assumption you will use.
5. Immediately continue using those assumptions.
6. Do not pause for confirmation unless continuing could:

   * delete unrelated user data,
   * expose credentials,
   * spend significant money,
   * make the GitHub repository public,
   * remove existing cloud resources,
   * overwrite important global configuration.
7. Never install Codex, Claude Code, OpenCode, Aider, GitHub CLI or Render CLI.
8. You may install normal project dependencies inside an isolated project environment.
9. Do not claim anything works unless it has been tested.
10. Never expose, print, commit or log API keys.
11. Preserve unrelated files and existing Git changes.
12. Back up configuration files before modifying them.
13. Prefer generated profiles, environment overrides and isolated configuration directories over permanent global configuration edits.
14. Continue diagnosing and fixing errors until all locally executable quality checks pass.
15. Maintain a detailed `BUILD_REPORT.md` throughout development.

# Existing environment assumptions

The environment may contain:

* Git.
* GitHub CLI through the `gh` command.
* GitHub authentication already completed.
* A Render CLI executable named `render.exe` in the project root directory.
* A `.env` file containing possible provider API keys.
* Some coding CLI agents already installed.

Do not assume any of these are usable without checking.

## GitHub CLI

Check:

```text
gh --version
gh auth status
```

If authenticated, use `gh` for repository creation, pushes, pull requests, workflow inspection and CI debugging.

If GitHub authentication is missing, document the blocker and continue all local work. Do not request, generate or search for a GitHub token.

## Render CLI

A Render CLI executable may exist at:

```text
./render.exe
```

or on Windows PowerShell:

```text
.\render.exe
```

Do not install another Render CLI.

Detect the current shell and invoke the root-directory executable correctly.

Check:

```text
render.exe --version
render.exe whoami
```

Use the executable’s built-in help before assuming command syntax:

```text
render.exe --help
render.exe services --help
render.exe blueprints --help
```

If the executable is authenticated, use it for documentation deployment and deployment verification.

If it is not authenticated, document the blocker and complete all configuration and local verification.

Do not copy `render.exe` into source control. Ensure it is ignored by Git when appropriate.

## Environment variables and `.env`

A `.env` file may contain API keys for some providers.

Treat `.env` as sensitive.

Rules:

1. Ensure `.env` is excluded from Git before reading or using it.
2. Never print its full contents.
3. Never include its values in logs, reports, test output, screenshots, fixtures, documentation or Git commits.
4. Inspect only variable names when determining available providers.
5. Load values through a secure environment loader.
6. Use available provider keys only for optional live verification.
7. Never make the core implementation depend on any key being present.
8. Missing credentials must not fail normal tests, builds or CI.
9. Live provider tests must use tiny prompts and strict token limits.
10. Never automatically test every discovered key if doing so could create meaningful charges.
11. Redact keys in exceptions and subprocess output.
12. If a credential looks malformed, mark that provider as unavailable instead of repeatedly attempting requests.

Potential environment-variable names may include, but are not limited to:

* `OPENAI_API_KEY`
* `ANTHROPIC_API_KEY`
* `GEMINI_API_KEY`
* `GOOGLE_API_KEY`
* `DEEPSEEK_API_KEY`
* `GROQ_API_KEY`
* `CEREBRAS_API_KEY`
* `NVIDIA_API_KEY`
* `MISTRAL_API_KEY`
* `XAI_API_KEY`
* `TOGETHER_API_KEY`
* `FIREWORKS_API_KEY`
* `SAMBANOVA_API_KEY`
* `COHERE_API_KEY`
* `OPENROUTER_API_KEY`
* `AGENTROUTER_API_KEY`
* `FORGE_API_KEY`
* `BLUESMINDS_API_KEY`
* `PERPLEXITY_API_KEY`
* `CLOUDFLARE_API_TOKEN`
* `AZURE_OPENAI_API_KEY`

Do not assume these exact names are present. Support configurable environment-variable references.

# Product definition

Divine Router is a local-first, self-hostable AI API gateway.

Users can configure multiple API keys from different AI providers and gateways. Divine Router exposes unified OpenAI-compatible, Anthropic-compatible and automatic-routing APIs.

It must support:

* Explicit provider and model selection.
* Automatic application routing.
* OpenAI Chat Completions compatibility.
* OpenAI Responses API compatibility.
* Anthropic Messages compatibility.
* Streaming responses.
* Tool and function calling.
* Provider fallbacks.
* Retries and rate-limit handling.
* Model discovery.
* Provider health monitoring.
* Usage, latency and error tracking.
* Secure credential management.
* Integration wrappers for useful installed coding CLI agents.

Divine Router is infrastructure, not a chat application.

# Technology stack

Use this stack unless the existing repository clearly establishes a better compatible architecture:

* Python 3.12 or the newest stable compatible installed version.
* FastAPI.
* Uvicorn.
* Pydantic v2.
* Async `httpx`.
* Typer for CLI commands.
* Textual for the TUI.
* SQLite for local metadata and usage statistics.
* SQLAlchemy 2.x.
* Alembic for migrations.
* `keyring` for operating-system credential storage.
* Pytest.
* pytest-asyncio.
* respx.
* Ruff.
* mypy or pyright.
* MkDocs with Material for documentation.
* Docker using a non-root runtime user.
* GitHub Actions.

Use a `src/` package layout and modern `pyproject.toml`.

Do not introduce Redis, PostgreSQL, Kubernetes, a browser application or a JavaScript frontend in the initial implementation.

# Architecture

Create clearly separated modules for:

* API protocols.
* Authentication.
* Canonical internal requests and responses.
* Streaming events.
* Provider adapters.
* Provider configuration templates.
* Provider and model registry.
* Capability detection.
* Explicit model resolution.
* Automatic routing.
* Retry and fallback execution.
* Circuit breakers.
* Credential storage.
* Usage metering.
* Persistence.
* Configuration management.
* Logging and redaction.
* CLI.
* TUI.
* Coding-agent wrappers.

Use this general flow:

```text
Client protocol
→ Divine authentication
→ protocol parser
→ canonical request
→ explicit resolver or automatic router
→ capability validation
→ provider selection
→ retry and fallback executor
→ provider adapter
→ canonical response or stream
→ client protocol serializer
```

Do not mix protocol translation directly into provider-specific HTTP code.

Avoid giant files, giant classes and large provider-specific conditional chains.

# API surfaces

Implement the following endpoints.

## OpenAI Chat Completions

```text
POST /v1/chat/completions
```

Support at minimum:

* `model`
* `messages`
* `temperature`
* `top_p`
* `max_tokens`
* `max_completion_tokens`
* `stop`
* `stream`
* `tools`
* `tool_choice`
* `response_format`
* `seed`

Support OpenAI-style server-sent-event streaming.

Use OpenAI-compatible error envelopes.

Allow explicit provider/model identifiers:

```text
provider/model-name
```

Allow configured aliases such as:

* `fast`
* `cheap`
* `coding`
* `reasoning`
* `long-context`
* `vision`
* `default`
* `auto`

## OpenAI Responses API

```text
POST /v1/responses
```

This endpoint is required for Codex integration.

Implement a meaningful compatibility subset covering:

* `model`
* `input`
* `instructions`
* `stream`
* text input items
* assistant output messages
* function tools
* function calls
* function-call outputs
* reasoning-related fields when representable
* token usage
* request IDs
* Responses streaming lifecycle events

Do not simply redirect Responses requests to Chat Completions without proper translation.

Create explicit converters between Responses API items and Divine Router’s canonical representation.

Return clear compatibility errors for unsupported hosted tools or stateful features.

Do not silently discard unsupported fields.

## Anthropic Messages API

```text
POST /v1/messages
```

Support:

* `model`
* `system`
* `messages`
* text content blocks
* image blocks where supported
* `max_tokens`
* `temperature`
* `top_p`
* `top_k`
* `stop_sequences`
* `stream`
* `tools`
* `tool_choice`
* `tool_use`
* `tool_result`
* usage information
* Anthropic-compatible streaming events

Accept both:

```text
x-api-key
```

and:

```text
Authorization: Bearer
```

Recognize the `anthropic-version` header.

Also implement when practical:

```text
POST /v1/messages/count_tokens
```

## Automatic routing API

Implement:

```text
POST /v1/auto/chat/completions
```

Also allow:

```json
{
  "model": "auto"
}
```

on `/v1/chat/completions`.

Automatic routing is intended for normal applications and experiments.

Do not configure Codex, Claude Code, OpenCode or Aider wrappers to use automatic routing by default.

# Administrative endpoints

Implement:

* `GET /healthz`
* `GET /readyz`
* `GET /v1/models`
* `GET /v1/divine/providers`
* `GET /v1/divine/providers/health`
* `GET /v1/divine/usage`
* `GET /v1/divine/routes`

Generate an independent local Divine API token.

Require authentication by default, including on localhost.

Bind to:

```text
127.0.0.1
```

by default.

Require an explicit configuration option before binding to:

```text
0.0.0.0
```

# Provider architecture

Do not build a mostly duplicated HTTP client for every OpenAI-compatible provider.

Implement provider families:

1. `OpenAICompatibleProvider`
2. `AnthropicProvider`
3. `GeminiProvider`
4. Extension interfaces for Bedrock and Vertex AI

Each provider configuration should define:

* provider ID
* display name
* adapter family
* base URL
* credential reference
* authentication style
* additional headers
* model discovery endpoint
* timeout
* enabled state
* capability overrides
* retry policy
* trust level
* verification status

Supported verification statuses:

* `verified-live`
* `verified-mocked`
* `compatible-unverified`
* `experimental`
* `disabled`

Never mark a provider `verified-live` unless a successful live request was performed during this build.

# Initial provider catalogue

Create built-in configuration templates for:

## Direct providers

* OpenAI
* Anthropic
* Google Gemini
* DeepSeek
* Groq
* Cerebras
* NVIDIA NIM or NVIDIA API Catalog
* Mistral
* xAI
* Together AI
* Fireworks AI
* SambaNova
* Cohere
* Hugging Face Inference Providers
* Cloudflare Workers AI
* Perplexity
* Azure OpenAI
* Ollama
* LM Studio

Create experimental or extension configurations for:

* AWS Bedrock
* Google Vertex AI

Only include AnyScale if current official documentation confirms an active usable API.

## Aggregators and gateways

* OpenRouter
* AgentRouter
* Forge at `forge-ai.space`
* BluesMinds
* Generic custom OpenAI-compatible provider
* Generic custom Anthropic-compatible provider

Use the generic OpenAI-compatible adapter wherever appropriate.

Research current official provider documentation before fixing base URLs or authentication formats.

Do not invent endpoints.

Make provider base URLs editable.

# Model discovery and capabilities

Do not permanently depend on hardcoded current model IDs.

Implement model discovery where supported.

Cache results with expiration.

Allow manually configured models when discovery is unavailable.

Track model capabilities including:

* chat
* Responses API
* streaming
* tool calling
* parallel tool calling
* structured output
* JSON mode
* vision
* audio input
* reasoning
* reasoning-content exposure
* prompt caching
* context window
* maximum output tokens
* token counting
* embeddings

Before dispatching, validate required capabilities.

Never silently remove tools, images or structured-output requirements.

# Automatic routing

Automatic routing must be modular.

## Stage 1: deterministic filtering

Filter models using:

* enabled providers
* available credentials
* provider health
* context requirements
* tool requirements
* vision requirements
* structured-output requirements
* output-token requirements
* budget constraints
* latency preference
* allowlists
* denylists

## Stage 2: task classification and scoring

Implement a rule-based classifier first.

Task classes should include:

* simple chat
* extraction
* summarization
* coding
* debugging
* agentic tool use
* mathematical reasoning
* deep reasoning
* long-context analysis
* creative writing
* vision
* low-latency
* low-cost

Allow an optional LLM classifier.

Provide a configurable Groq classifier template, but do not permanently hardcode one Groq model.

The LLM classifier must:

* use strict structured JSON,
* use a small output-token budget,
* use a short timeout,
* fall back to deterministic routing,
* avoid sending the full prompt when a shortened sample is enough,
* warn that classification may expose content to another provider,
* be disableable globally and per request,
* avoid classifying secrets, tool outputs or entire large codebases.

Return routing metadata in headers:

* `x-divine-provider`
* `x-divine-model`
* `x-divine-route`
* `x-divine-fallback-count`
* `x-divine-request-id`

Support optional routing controls:

* `x-divine-max-cost`
* `x-divine-prefer`
* `x-divine-deny-provider`
* `x-divine-disable-fallback`
* `x-divine-disable-classifier`

Validate all values.

# Reliability

Implement:

* provider-specific timeouts
* exponential backoff with jitter
* retry classification
* `Retry-After` handling
* fallback chains
* circuit breakers
* provider health scoring
* total request deadlines
* streaming idle timeouts
* client-disconnect cancellation
* request IDs
* structured logs

Do not blindly retry partially streamed requests.

Once streamed output has started, do not restart against another provider and duplicate content.

# Credentials and security

Never store provider API keys directly in SQLite.

Credential priority:

1. Operating-system keyring.
2. Environment-variable references.
3. Encrypted local credential file when keyring is unavailable.

For encrypted-file fallback:

* use trusted authenticated encryption,
* require a master password or master-key environment variable,
* apply restrictive file permissions,
* never implement custom cryptography.

Implement centralized redaction for:

* API keys
* authorization headers
* cookies
* provider tokens
* webhook URLs
* query-string secrets

Do not log raw prompts or responses by default.

Allow content logging only through explicit opt-in configuration with a warning.

Additional security:

* protect administration endpoints,
* disable CORS by default,
* limit request-body size,
* add configurable local rate limiting,
* validate imported configuration,
* use atomic configuration writes,
* create configuration backups,
* prevent path traversal,
* prevent secrets from appearing in exception serialization.

# TUI and CLI

The TUI is for configuration and operations, not chatting.

Main command:

```text
divine
```

Commands:

* `divine tui`
* `divine serve`
* `divine start`
* `divine stop`
* `divine restart`
* `divine status`
* `divine doctor`
* `divine providers`
* `divine models`
* `divine routes`
* `divine logs`
* `divine test-provider PROVIDER`
* `divine config export`
* `divine config import`

The Textual TUI should include:

* Dashboard
* Provider configuration
* Credentials
* Models
* Aliases
* Routing policies
* Fallback chains
* CLI-agent profiles
* Server settings
* Usage statistics
* Provider health
* Diagnostics
* Redacted logs

Prioritize keyboard navigation, readability and stability over decorative animation.

# Coding-agent wrappers

Detect whether these are installed:

* Claude Code
* Codex CLI
* OpenCode
* Aider

Only integrate installed agents.

Provide commands:

* `divine-claude`
* `divine-codex`
* `divine-opencode`
* `divine-aider`

Each wrapper must:

1. Forward normal CLI arguments.
2. Start Divine Router when necessary unless disabled.
3. Use an explicit configured model or alias.
4. Never use automatic routing by default.
5. Use temporary or isolated configuration.
6. Preserve the user's existing configuration.
7. Clean temporary state on exit.
8. Forward operating-system signals.
9. Preserve child exit codes.
10. Handle spaces in paths.
11. Never print credentials.
12. Provide `--dry-run`.
13. Provide `--model`.
14. Provide `--profile`.
15. Fail clearly when the underlying CLI is unavailable.

## Claude Code

Use the currently documented Anthropic gateway configuration mechanism.

Route Claude Code to Divine Router’s Anthropic Messages-compatible API.

Do not overwrite the user’s normal Claude login.

## Codex CLI

Use a temporary or dedicated Codex configuration profile.

Route Codex to:

```text
/v1/responses
```

Use the Responses wire protocol.

Do not overwrite the user’s main Codex configuration.

Inspect the installed Codex version and configuration schema before generating a profile.

## OpenCode

Use supported custom-provider configuration.

Prefer an isolated generated config or environment override.

Do not permanently change normal OpenCode settings.

## Aider

Create the wrapper only when Aider is installed and its installed version supports a reliable base-URL override.

# Configuration

Use a human-readable TOML configuration file.

Use platform-appropriate configuration directories:

* XDG paths on Linux.
* Application Support on macOS.
* AppData on Windows.

Configuration should support:

* server settings
* providers
* credential references
* aliases
* capability overrides
* fallback chains
* routing policies
* classifier settings
* CLI profiles
* logging
* usage retention
* pricing metadata

Implement:

* schema versioning
* configuration migration
* atomic writes
* automatic backups
* validation
* fake-key example configuration

# Observability

Store metadata by default, not prompt contents.

Record:

* request ID
* timestamp
* client type
* requested model
* selected model
* selected provider
* route
* fallback attempts
* status
* total latency
* time to first token
* input tokens
* output tokens
* estimated cost
* error category

Pricing information must be editable and date-stamped.

Do not present stale pricing as guaranteed current pricing.

# Documentation files

Create:

* `README.md`
* `ARCHITECTURE.md`
* `SECURITY.md`
* `CONTRIBUTING.md`
* `PROVIDER_COMPATIBILITY.md`
* `CLI_INTEGRATIONS.md`
* `AUTO_ROUTING.md`
* `BUILD_REPORT.md`
* `CHANGELOG.md`
* `LICENSE`

The README must include:

* project purpose
* architecture overview
* installation
* quick start
* TUI usage
* API examples
* OpenAI SDK example
* Anthropic SDK example
* Responses API example
* wrapper usage
* provider configuration
* security warning
* tests
* Docker
* limitations

`PROVIDER_COMPATIBILITY.md` must distinguish:

* template exists
* mock-tested
* live-tested
* streaming tested
* tool calls tested
* known limitations

Do not overstate compatibility.

# Documentation website

Create a polished documentation website using MkDocs with Material.

Use:

```text
docs/
mkdocs.yml
```

Add documentation dependencies as a dedicated optional dependency group.

The site must include:

* Home
* Installation
* Quick start
* Configuration
* Provider setup
* Provider compatibility matrix
* Chat Completions API
* Responses API
* Anthropic Messages API
* Automatic routing
* Aliases
* Fallback chains
* CLI reference
* TUI guide
* Claude Code integration
* Codex integration
* OpenCode integration
* Aider integration when available
* Security
* Self-hosting
* Architecture
* Troubleshooting
* Contributing
* Changelog
* Limitations

Include tested examples using:

* `curl`
* OpenAI Python SDK
* Anthropic Python SDK

The site should provide:

* search
* syntax highlighting
* copyable code
* dark and light mode
* responsive navigation
* repository link
* version information
* useful metadata
* a restrained Divine Router visual identity

Do not create a custom React documentation application.

Validate using:

```text
mkdocs build --strict
```

Treat warnings and broken internal links as failures.

Documentation must be updated alongside features, not left until the end.

# Render documentation deployment

Deploy the MkDocs website as a public Render Static Site.

This instruction authorizes public deployment of the documentation website.

It does not authorize making the GitHub repository public.

Create a root-level:

```text
render.yaml
```

Use:

* a Render Static Site
* an appropriate free plan where available
* build command that installs documentation dependencies and runs `mkdocs build --strict`
* publish directory `site`
* automatic deployment from the active development branch
* a unique service name based on `divine-router-docs`

Use the root-directory `render.exe`.

Before deployment:

1. Verify authentication with `render.exe whoami`.
2. Inspect the installed CLI version.
3. Inspect help for service and Blueprint commands.
4. Determine the current Render workspace.
5. Validate the Blueprint using the command supported by the installed CLI.
6. Do not assume outdated command flags.

If a Divine Router documentation service already exists:

* inspect it,
* reuse it when it belongs to this repository,
* avoid creating duplicates,
* never delete it without explicit authorization.

If Render cannot access the private GitHub repository, document the exact blocker.

Do not make the repository public as a workaround.

## Render deployment verification

After creating or updating the service:

1. Trigger the deployment.
2. Inspect deployment status.
3. Monitor logs.
4. Fix build failures.
5. Commit and push fixes.
6. Trigger or observe redeployment.
7. Repeat until successful or blocked by external authorization.
8. Retrieve the public `onrender.com` URL.
9. Send HTTP requests to the deployed site.
10. Verify the home page.
11. Verify installation documentation.
12. Verify API documentation.
13. Verify at least one CLI integration page.
14. Verify static assets.
15. Check that no secrets were published.

Verify automatic deployment:

1. Make a visible documentation update after the first successful deployment.
2. Commit and push it.
3. Confirm Render starts a new deployment.
4. Confirm the deployed site includes the update.

Do not claim Render deployment is verified merely because `render.yaml` exists.

# Testing

Create a serious automated test suite.

## Unit tests

Cover:

* protocol parsing
* canonical conversions
* provider authentication
* error normalization
* model resolution
* capability validation
* routing constraints
* routing scoring
* retry classification
* fallback behavior
* circuit breakers
* credential redaction
* configuration migration
* wrapper command generation

## Mocked integration tests

Cover:

* OpenAI Chat Completions
* OpenAI Responses
* Anthropic Messages
* streaming
* tool calls
* rate limits
* timeouts
* malformed responses
* mid-stream failures
* fallback selection

## SDK compatibility smoke tests

Use official OpenAI and Anthropic Python SDKs against the local server.

Test:

* non-streaming Chat Completions
* streaming Chat Completions
* non-streaming Messages
* streaming Messages
* tool calls
* representative Responses API request
* error responses

## Wrapper tests

Use fake executable fixtures to verify:

* argument forwarding
* environment variables
* isolated configuration
* preservation of existing configuration
* exit-code forwarding
* redaction
* dry-run output

## Live provider tests

Live tests must be optional:

```text
DIVINE_LIVE_TESTS=1
```

Only run a provider live test when:

* its credential exists,
* the credential is loaded securely,
* the test can use a very small request,
* the provider is enabled for live testing.

Missing credentials must not fail the test suite.

Produce a live-test matrix.

Never print credentials.

Do not repeatedly retry authentication failures.

# Quality gates

The project is not complete until all available checks pass:

* formatting
* linting
* static typing
* unit tests
* integration tests
* SDK smoke tests
* at least 85% coverage for core routing and protocol modules
* Python package build
* clean temporary-environment installation
* CLI help checks
* server startup smoke test
* documentation strict build
* Docker build where Docker is available
* tracked-file secret scan
* Git diff review

Run the full quality suite after major milestones and at the end.

# Packaging

Make Divine Router installable as a Python package.

Expected commands:

* `divine`
* `divine-claude`
* `divine-codex`
* `divine-opencode`
* `divine-aider`

Provide:

* wheel
* source distribution
* Dockerfile
* optional `docker-compose.yml` only when useful
* systemd user-service example
* Windows startup instructions

Do not require administrator or root access.

# Git workflow

Inspect the existing repository before making changes.

If it is an existing repository:

* preserve unrelated changes,
* create a branch such as `feat/divine-router`,
* do not rewrite unrelated history.

If no repository exists:

1. Initialize Git.
2. Create `.gitignore`.
3. Ensure `.env`, credentials, databases, logs, build artifacts, temporary configuration and `render.exe` are ignored.
4. Create an initial repository scaffold commit.

If GitHub CLI is authenticated and no remote exists:

1. Create a private GitHub repository named `divine-router`.
2. Add it as the remote.
3. Push the initial branch.
4. Never create a public repository without explicit approval.

Use conventional commits.

Examples:

* `chore: initialize divine router project`
* `feat: add canonical request models`
* `feat: implement openai chat completions`
* `feat: implement anthropic messages compatibility`
* `feat: add provider fallback engine`
* `test: add streaming compatibility coverage`
* `docs: add provider configuration guide`

## Incremental commits and pushes

Do not build the entire project and push only once at the end.

After every completed and locally tested feature or development milestone:

1. Review the diff.
2. Run relevant tests.
3. Check staged files for secrets.
4. Create a logical conventional commit.
5. Immediately push the feature branch.
6. Inspect the corresponding GitHub Actions run.
7. Fix known CI failures before proceeding significantly further when practical.
8. Push the fixes.
9. Confirm that the updated CI run passes.

Push the repository scaffold early.

Push after each major phase and after meaningful features inside large phases.

Do not accumulate unrelated features in one commit.

Never knowingly push broken code or secrets.

## Documentation with feature commits

When a feature changes user-facing behavior:

1. Update its documentation in the same milestone.
2. Commit the code and documentation logically.
3. Push immediately.
4. Verify GitHub Actions.
5. Verify the Render documentation deployment when the site is already active.

# GitHub Actions CI/CD

Create GitHub Actions workflows.

## CI workflow

Run on pushes and pull requests.

Test on:

* Ubuntu
* Windows
* macOS where practical

Use a reasonable Python-version matrix.

Run:

* dependency installation
* Ruff formatting check
* linting
* static type checking
* tests
* coverage
* package build
* documentation strict build
* Docker build on Linux when supported
* tracked-file secret scanning

## Documentation workflow

Run:

```text
mkdocs build --strict
```

Check internal links when practical.

Ensure generated `site/` output is not accidentally committed unless intentionally required.

## Release workflow

On version tags:

* build wheel
* build source distribution
* generate checksums
* create GitHub release artifacts
* build and publish a container image to GitHub Container Registry when permissions permit

Do not publish to PyPI unless trusted publishing or proper secrets are already configured.

## Dependency maintenance

Add Dependabot or an equivalent minimal dependency-update configuration.

## CI verification

When authenticated:

1. Push each milestone.
2. Use `gh run list`.
3. Use `gh run view`.
4. Inspect failing logs.
5. Fix problems.
6. Push corrections.
7. Repeat until green or blocked externally.

Do not claim CI is verified based only on workflow YAML.

If remote CI cannot run, execute equivalent commands locally and document that remote verification remains incomplete.

# Development phases

## Phase 1: preflight and repository

* Inspect environment.
* Check Git.
* Check `gh`.
* Check `render.exe`.
* Protect `.env`.
* Detect installed CLI agents.
* Initialize repository if required.
* Create private GitHub repository if authorized and needed.
* Push the initial scaffold.

## Phase 2: architecture and project foundation

* Create package layout.
* Add configuration schema.
* Add canonical protocol models.
* Add logging and redaction.
* Add persistence.
* Configure quality tools.
* Test, document, commit and push.

## Phase 3: core gateway

* Authentication.
* Chat Completions endpoint.
* Generic OpenAI-compatible provider.
* Streaming.
* Error normalization.
* Mocked tests.
* SDK smoke tests.
* Documentation.
* Commit and push.

## Phase 4: protocol compatibility

* Anthropic Messages.
* OpenAI Responses.
* Translation layers.
* Streaming compatibility.
* Tool calls.
* Tests.
* Documentation.
* Commit and push each substantial protocol milestone separately.

## Phase 5: routing and reliability

* Model resolver.
* Capability filtering.
* Rule-based routing.
* Optional LLM classifier.
* Fallbacks.
* Retries.
* Circuit breakers.
* Usage tracking.
* Tests.
* Documentation.
* Incremental commits and pushes.

## Phase 6: provider catalogue

* Provider templates.
* Model discovery.
* Capability registry.
* Mocked tests.
* Optional live tests using available `.env` credentials.
* Compatibility matrix.
* Incremental commits and pushes.

## Phase 7: TUI and CLI wrappers

* TUI.
* Server lifecycle commands.
* Claude Code wrapper.
* Codex wrapper.
* OpenCode wrapper.
* Aider wrapper where supported.
* Wrapper tests.
* Documentation.
* Incremental commits and pushes.

## Phase 8: documentation website

* Build MkDocs site.
* Run strict build.
* Add Render Blueprint.
* Validate Render configuration.
* Commit and push.
* Create Render service.
* Verify deployment.
* Fix deployment errors.
* Verify automatic redeployment after another documentation commit.

## Phase 9: packaging and deployment support

* Package builds.
* Docker.
* systemd example.
* Windows instructions.
* Release workflows.
* Commit and push.

## Phase 10: final verification

* Clean-environment installation.
* Full tests.
* Coverage.
* Linting.
* Typing.
* Documentation.
* Secret scan.
* Git review.
* CI verification.
* Render verification.
* Final build report.

# Scope control

Prioritize:

1. correct architecture,
2. protocol compatibility,
3. security,
4. tests,
5. useful wrappers,
6. reliable routing,
7. provider templates,
8. visual polish.

A generic OpenAI-compatible adapter with strong provider configuration is better than many duplicated adapters.

Do not generate placeholder implementations and call them complete.

Use explicit compatibility errors when a feature cannot be represented.

Do not let missing provider keys block the core gateway.

Do not let inability to live-test one provider prevent mocked compatibility support.

Clearly distinguish:

* implemented
* mock-tested
* live-tested
* experimental
* unsupported

# Final output

At completion, print and save in `BUILD_REPORT.md`:

1. Repository path.
2. Active branch.
3. GitHub repository URL.
4. Git remote.
5. Latest commit.
6. Commit history summary.
7. Installation command.
8. TUI launch command.
9. Server start command.
10. Endpoint URLs.
11. Available wrapper commands.
12. Test summary.
13. Coverage summary.
14. Package-build status.
15. Docker-build status.
16. GitHub Actions run URLs and statuses.
17. Documentation framework.
18. Documentation source directory.
19. Local documentation command.
20. Render service name.
21. Render deployment URL.
22. Render deployment status.
23. Deployed branch.
24. Last verified deployment commit.
25. Whether automatic Render redeployment was verified.
26. Providers live-tested.
27. Providers mock-tested.
28. Providers unverified.
29. Installed CLI agents detected.
30. Known limitations.
31. External blockers.
32. Files requiring manual review.
33. Remaining operator actions.

Begin now.
