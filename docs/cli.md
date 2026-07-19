# CLI reference

Running `divine` without a subcommand opens the TUI.

| Command | Purpose |
|---|---|
| `divine tui` | Open operations/configuration UI |
| `divine serve` | Foreground authenticated server |
| `divine start` | Background server |
| `divine stop` | Stop only a fingerprinted owned process |
| `divine restart` | Stop and start |
| `divine status` | Process plus authenticated health status |
| `divine doctor` | Validate config and report credential availability without values |
| `divine providers` | Provider template/status list |
| `divine models` | Registered model IDs |
| `divine routes` | Redacted aliases and fallback chains |
| `divine logs --lines N` | Recent structured server log |
| `divine test-provider ID` | Read-only model discovery check |
| `divine config export [FILE]` | TOML to stdout or atomic file export |
| `divine config import FILE` | Validate, back up, and import TOML |

`test-provider` may call the upstream provider and therefore requires an enabled provider and valid
credential. It reports counts, never credential values.

## Wrapper commands

```console
divine-claude --dry-run --model provider/model -p "hello"
divine-codex --dry-run --model provider/model exec "hello"
divine-opencode --dry-run --model provider/model run "hello"
```

Wrapper-owned options are `--dry-run`, `--model`, `--profile`, and `--no-start`; all other
arguments are forwarded in order. Dry-run output redacts the Divine token.
