# Installation

Divine Router requires Python 3.12 or newer. Use an isolated environment; administrator access is
not required.

=== "Windows PowerShell"

    ```powershell
    py -3.13 -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -e .
    divine doctor
    ```

=== "Linux or macOS"

    ```bash
    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install -e .
    divine doctor
    ```

For development and documentation, install optional groups:

```console
python -m pip install -e ".[test,docs]"
```

`divine doctor` creates validated default configuration and an independent random API token in
the platform configuration directory:

| Platform | Configuration convention |
|---|---|
| Windows | `%APPDATA%\divine-router` |
| macOS | `~/Library/Application Support/divine-router` |
| Linux | `$XDG_CONFIG_HOME/divine-router` or `~/.config/divine-router` |

Set `DIVINE_CONFIG_DIR`, `DIVINE_DATA_DIR`, `DIVINE_CACHE_DIR`, and `DIVINE_LOG_DIR` to isolate
an installation or test run. Relative values are resolved to absolute paths.

## Package artifacts

Build a wheel and source distribution with:

```console
python -m build
```

The installed entry points are `divine`, `divine-claude`, `divine-codex`, `divine-opencode`, and
`divine-aider`.

Next: [configure and start the router](quick-start.md).
