"""Typer command-line interface and local server lifecycle management."""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import httpx
import psutil
import typer
import uvicorn
from dotenv import load_dotenv

from divine_router.api.app import create_app
from divine_router.config.manager import ConfigManager
from divine_router.config.models import DivineConfig
from divine_router.paths import DivinePaths
from divine_router.persistence.database import Database
from divine_router.providers.catalog import built_in_providers
from divine_router.security.auth import load_or_create_token
from divine_router.security.credentials import CredentialStore
from divine_router.service import Gateway
from divine_router.tui import run_tui

app = typer.Typer(no_args_is_help=True, help="Operate the local Divine Router AI API gateway.")
config_app = typer.Typer(help="Export or import validated TOML configuration.")
app.add_typer(config_app, name="config")


def default_config() -> DivineConfig:
    return DivineConfig(
        providers=built_in_providers(),
        aliases={
            "default": [],
            "fast": [],
            "cheap": [],
            "coding": [],
            "reasoning": [],
            "long-context": [],
            "vision": [],
        },
    )


def runtime() -> tuple[DivinePaths, DivineConfig, str, Gateway, Database]:
    paths = DivinePaths.discover()
    manager = ConfigManager(paths.config_file)
    if not paths.config_file.exists():
        manager.save(default_config())
    config = manager.load()
    load_dotenv(Path.cwd() / ".env", override=False)
    token = load_or_create_token(paths.token_file)
    credentials = CredentialStore(paths.config_dir / "credentials.enc")
    gateway = Gateway.from_config(config, credentials)
    return paths, config, token, gateway, Database(paths.database_file)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Open the operations TUI when no subcommand is supplied."""
    if ctx.invoked_subcommand is None:
        run_tui()


@app.command()
def tui() -> None:
    """Open the Textual configuration and operations interface."""
    run_tui()


@app.command()
def serve() -> None:
    """Run the authenticated foreground API server."""
    _, config, token, gateway, database = runtime()
    api = create_app(config, gateway, token, database)
    uvicorn.run(api, host=config.server.host, port=config.server.port, log_config=None)


def _pid_file(paths: DivinePaths) -> Path:
    return paths.data_dir / "server.pid"


def _read_process_record(paths: DivinePaths) -> tuple[int, float] | None:
    try:
        payload = json.loads(_pid_file(paths).read_text(encoding="utf-8"))
        return int(payload["pid"]), float(payload["created"])
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _owned_process(record: tuple[int, float] | None) -> psutil.Process | None:
    """Return a live Divine process only when PID and creation fingerprint match."""
    if record is None:
        return None
    pid, created = record
    try:
        process = psutil.Process(pid)
        if abs(process.create_time() - created) > 0.01:
            return None
        command = " ".join(process.cmdline()).lower().replace("\\", "/")
    except (psutil.Error, OSError):
        return None
    return process if "divine_router.cli" in command and "serve" in command else None


@app.command()
def start() -> None:
    """Start Divine Router in the background without administrator access."""
    paths = DivinePaths.discover()
    existing = _owned_process(_read_process_record(paths))
    if existing is not None:
        typer.echo(f"Divine Router is already running (PID {existing.pid}).")
        return
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    paths.log_dir.mkdir(parents=True, exist_ok=True)
    log_handle = (paths.log_dir / "server.log").open("a", encoding="utf-8")
    flags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
    process = subprocess.Popen(
        [sys.executable, "-m", "divine_router.cli", "serve"],
        stdin=subprocess.DEVNULL,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=flags,
        close_fds=os.name != "nt",
    )
    log_handle.close()
    record = {"pid": process.pid, "created": psutil.Process(process.pid).create_time()}
    _pid_file(paths).write_text(json.dumps(record), encoding="utf-8")
    typer.echo(f"Started Divine Router (PID {process.pid}).")


@app.command()
def stop() -> None:
    """Stop the background server started by Divine Router."""
    paths = DivinePaths.discover()
    process = _owned_process(_read_process_record(paths))
    if process is None:
        _pid_file(paths).unlink(missing_ok=True)
        typer.echo("Divine Router is not running.")
        return
    pid = process.pid
    process.send_signal(signal.SIGTERM)
    _pid_file(paths).unlink(missing_ok=True)
    typer.echo(f"Stopped Divine Router (PID {pid}).")


@app.command()
def restart() -> None:
    """Restart the background server."""
    stop()
    start()


@app.command()
def status() -> None:
    """Show local process and authenticated API status."""
    paths = DivinePaths.discover()
    process = _owned_process(_read_process_record(paths))
    if process is None:
        typer.echo("stopped")
        raise typer.Exit(1)
    pid = process.pid
    config = ConfigManager(paths.config_file).load()
    token = load_or_create_token(paths.token_file)
    try:
        response = httpx.get(
            f"http://{config.server.host}:{config.server.port}/healthz",
            headers={"Authorization": f"Bearer {token}"},
            timeout=2,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        typer.echo(f"process-running-unhealthy pid={pid}")
        raise typer.Exit(2) from None
    typer.echo(f"running pid={pid}")


@app.command()
def doctor() -> None:
    """Validate local configuration and report credential availability without values."""
    paths, config, _, gateway, _ = runtime()
    typer.echo(f"config: valid ({paths.config_file})")
    typer.echo(f"bind: {config.server.host}:{config.server.port}")
    typer.echo(f"enabled providers with credentials: {len(gateway.providers)}")
    typer.echo(f"registered models: {len(gateway.registry.all())}")


@app.command()
def providers() -> None:
    """List provider templates and verification status."""
    _, config, _, _, _ = runtime()
    for provider in config.providers:
        state = "enabled" if provider.enabled else "disabled"
        typer.echo(f"{provider.id}\t{state}\t{provider.verification}")


@app.command()
def models() -> None:
    """List configured model identifiers."""
    _, _, _, gateway, _ = runtime()
    for model in gateway.registry.all():
        typer.echo(model.qualified_id)


@app.command()
def routes() -> None:
    """Print aliases and fallback chains as JSON."""
    _, config, _, _, _ = runtime()
    typer.echo(
        json.dumps({"aliases": config.aliases, "fallback_chains": config.fallback_chains}, indent=2)
    )


@app.command()
def logs(lines: Annotated[int, typer.Option(min=1, max=1000)] = 100) -> None:
    """Show recent structured server logs (content logging is off by default)."""
    path = DivinePaths.discover().log_dir / "server.log"
    if not path.exists():
        typer.echo("No server log exists.")
        return
    recent = path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
    typer.echo("\n".join(recent))


@app.command("test-provider")
def test_provider(provider_id: str) -> None:
    """Perform a read-only model-discovery check for one configured provider."""
    _, _, _, gateway, _ = runtime()
    provider = gateway.providers.get(provider_id)
    if not provider:
        typer.echo("Provider is disabled or its credential is unavailable.", err=True)
        raise typer.Exit(1)
    discovered = asyncio.run(provider.discover_models())
    typer.echo(f"Provider responded with {len(discovered)} model(s).")


@config_app.command("export")
def export_config(destination: Path | None = None) -> None:
    """Export validated configuration containing references, never secret values."""
    paths = DivinePaths.discover()
    config = ConfigManager(paths.config_file).load()
    if destination is None:
        typer.echo(ConfigManager.dumps(config))
        return
    ConfigManager(destination).save(config)
    typer.echo(f"Exported configuration to {destination.resolve()}")


@config_app.command("import")
def import_config(source: Path) -> None:
    """Validate and atomically import TOML configuration with an automatic backup."""
    source_path = source.resolve(strict=True)
    imported = ConfigManager(source_path).load()
    destination = ConfigManager(DivinePaths.discover().config_file)
    backup = destination.save(imported)
    typer.echo(f"Imported configuration; backup={backup or 'not-required'}")


if __name__ == "__main__":
    app()
