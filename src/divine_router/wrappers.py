"""Isolated wrappers for installed coding CLI agents."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx

from divine_router.config.manager import ConfigManager
from divine_router.paths import DivinePaths
from divine_router.security.auth import load_or_create_token

AgentName = Literal["claude", "codex", "opencode", "aider"]


@dataclass(frozen=True, slots=True)
class LaunchPlan:
    agent: AgentName
    executable: str
    arguments: list[str]
    environment: dict[str, str]
    model: str
    config_paths: tuple[Path, ...] = ()

    def redacted(self) -> dict[str, Any]:
        sensitive = {
            "DIVINE_API_TOKEN",
            "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
        }
        return {
            "agent": self.agent,
            "executable": self.executable,
            "arguments": self.arguments,
            "model": self.model,
            "environment": {
                key: "[REDACTED]" if key in sensitive else value
                for key, value in self.environment.items()
                if key in sensitive
                or key
                in {
                    "CODEX_HOME",
                    "CLAUDE_CONFIG_DIR",
                    "ANTHROPIC_BASE_URL",
                    "OPENCODE_CONFIG",
                    "OPENCODE_CONFIG_DIR",
                }
            },
        }


def _server_details() -> tuple[str, str]:
    paths = DivinePaths.discover()
    config = ConfigManager(paths.config_file).load()
    token = load_or_create_token(paths.token_file)
    return f"http://{config.server.host}:{config.server.port}", token


def _model(agent: AgentName, requested: str | None, profile: str | None) -> str:
    if requested:
        if requested == "auto":
            raise ValueError("coding-agent wrappers cannot use automatic routing")
        return requested
    config = ConfigManager(DivinePaths.discover().config_file).load()
    if profile:
        configured = config.cli_profiles.get(profile, {}).get("model")
        if isinstance(configured, str) and configured and configured != "auto":
            return configured
    environment = os.environ.get(f"DIVINE_{agent.upper()}_MODEL")
    if environment and environment != "auto":
        return environment
    return "coding"


def build_launch_plan(
    agent: AgentName,
    temporary: Path,
    *,
    model: str,
    forwarded: list[str],
    server_url: str,
    token: str,
) -> LaunchPlan:
    executable = shutil.which(agent)
    if not executable:
        raise FileNotFoundError(f"underlying {agent} CLI is not installed")
    environment: dict[str, str] = {}
    arguments = list(forwarded)
    config_paths: list[Path] = []
    if agent == "claude":
        config_dir = temporary / "claude"
        config_dir.mkdir(parents=True)
        settings = config_dir / "settings.json"
        settings.write_text('{"permissions":{"defaultMode":"manual"}}', encoding="utf-8")
        environment.update(
            {
                "CLAUDE_CONFIG_DIR": str(config_dir),
                "ANTHROPIC_BASE_URL": server_url,
                "ANTHROPIC_AUTH_TOKEN": token,
                "ANTHROPIC_MODEL": model,
            }
        )
        arguments = ["--settings", str(settings), "--model", model, *arguments]
        config_paths.append(settings)
    elif agent == "codex":
        codex_home = temporary / "codex"
        codex_home.mkdir(parents=True)
        config_path = codex_home / "config.toml"
        config_path.write_text(
            "\n".join(
                [
                    f"model = {json.dumps(model)}",
                    'model_provider = "divine"',
                    "",
                    "[model_providers.divine]",
                    'name = "Divine Router"',
                    f"base_url = {json.dumps(server_url + '/v1')}",
                    'env_key = "DIVINE_API_TOKEN"',
                    'wire_api = "responses"',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        environment.update({"CODEX_HOME": str(codex_home), "DIVINE_API_TOKEN": token})
        arguments = ["--strict-config", "--model", model, *arguments]
        config_paths.append(config_path)
    elif agent == "opencode":
        config_dir = temporary / "opencode"
        data_dir = temporary / "opencode-data"
        config_dir.mkdir(parents=True)
        data_dir.mkdir(parents=True)
        config_path = config_dir / "opencode.json"
        config_path.write_text(
            json.dumps(
                {
                    "$schema": "https://opencode.ai/config.json",
                    "model": f"divine/{model}",
                    "share": "disabled",
                    "provider": {
                        "divine": {
                            "npm": "@ai-sdk/openai-compatible",
                            "name": "Divine Router",
                            "options": {
                                "baseURL": f"{server_url}/v1",
                                "apiKey": "{env:DIVINE_API_TOKEN}",
                            },
                            "models": {model: {"name": model}},
                        }
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        environment.update(
            {
                "OPENCODE_CONFIG": str(config_path),
                "OPENCODE_CONFIG_DIR": str(config_dir),
                "XDG_DATA_HOME": str(data_dir),
                "DIVINE_API_TOKEN": token,
                "OPENCODE_DISABLE_AUTOUPDATE": "true",
            }
        )
        arguments = ["--pure", "--model", f"divine/{model}", *arguments]
        config_paths.append(config_path)
    else:
        raise FileNotFoundError("Aider is not installed or lacks a verified isolated base-URL flow")
    return LaunchPlan(agent, executable, arguments, environment, model, tuple(config_paths))


def _ensure_server(server_url: str, token: str) -> subprocess.Popen[bytes] | None:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        httpx.get(f"{server_url}/healthz", headers=headers, timeout=1).raise_for_status()
        return None
    except httpx.HTTPError:
        pass
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(
        [sys.executable, "-m", "divine_router.cli", "serve"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
        close_fds=os.name != "nt",
    )
    for _ in range(40):
        if process.poll() is not None:
            raise RuntimeError("Divine Router failed to start")
        try:
            httpx.get(f"{server_url}/healthz", headers=headers, timeout=0.5).raise_for_status()
            return process
        except httpx.HTTPError:
            time.sleep(0.25)
    process.terminate()
    raise RuntimeError("Divine Router did not become healthy within 10 seconds")


def _run(agent: AgentName) -> None:
    parser = argparse.ArgumentParser(prog=f"divine-{agent}")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--profile")
    parser.add_argument("--no-start", action="store_true")
    options, forwarded = parser.parse_known_args()
    try:
        model = _model(agent, options.model, options.profile)
        server_url, token = _server_details()
        with tempfile.TemporaryDirectory(prefix=f"divine-{agent}-") as temporary_name:
            plan = build_launch_plan(
                agent,
                Path(temporary_name),
                model=model,
                forwarded=forwarded,
                server_url=server_url,
                token=token,
            )
            if options.dry_run:
                print(json.dumps(plan.redacted(), indent=2))
                raise SystemExit(0)
            server = None if options.no_start else _ensure_server(server_url, token)
            environment = os.environ.copy()
            environment.update(plan.environment)
            child = subprocess.Popen([plan.executable, *plan.arguments], env=environment)  # noqa: S603
            previous: dict[signal.Signals, Any] = {}

            def forward(signum: int, _: Any) -> None:
                child.send_signal(signum)

            for signum in (signal.SIGINT, signal.SIGTERM):
                previous[signum] = signal.signal(signum, forward)
            try:
                code = child.wait()
            finally:
                for restore_signum, handler in previous.items():
                    signal.signal(restore_signum, handler)
                if server is not None and server.poll() is None:
                    server.terminate()
            raise SystemExit(code)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"divine-{agent}: {exc}", file=sys.stderr)
        raise SystemExit(2) from None


def claude_main() -> None:
    _run("claude")


def codex_main() -> None:
    _run("codex")


def opencode_main() -> None:
    _run("opencode")


def aider_main() -> None:
    _run("aider")
