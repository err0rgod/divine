# OpenCode integration

`divine-opencode` creates an isolated OpenCode JSON configuration using the
`@ai-sdk/openai-compatible` provider and Divine Router's `/v1` base URL. It sets
`OPENCODE_CONFIG`, `OPENCODE_CONFIG_DIR`, an isolated data directory, disables sharing, and
disables automatic updates for that run.

```console
divine-opencode --model provider/model run "Review this small patch"
```

The API key in generated JSON is an environment reference, not a token value. Normal OpenCode
configuration and data remain untouched. The wrapper forwards child exit status and operating
system signals.
