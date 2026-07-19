from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

from divine_router import wrappers
from divine_router.wrappers import LaunchPlan, build_launch_plan


@pytest.mark.parametrize("agent", ["claude", "codex", "opencode"])
def test_launch_plans_are_isolated_and_forward_arguments(
    agent: wrappers.AgentName,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = tmp_path / "operator-config"
    existing.write_text("preserve-me", encoding="utf-8")
    monkeypatch.setattr(shutil, "which", lambda _: "C:/fake/agent.exe")

    plan = build_launch_plan(
        agent,
        tmp_path / "isolated",
        model="provider/coding-model",
        forwarded=["run", "--flag", "value with spaces"],
        server_url="http://127.0.0.1:8742",
        token="divine-secret-token",
    )

    assert plan.arguments[-3:] == ["run", "--flag", "value with spaces"]
    assert plan.model == "provider/coding-model"
    assert plan.config_paths and all(
        path.is_relative_to(tmp_path / "isolated") for path in plan.config_paths
    )
    assert existing.read_text(encoding="utf-8") == "preserve-me"
    for path in plan.config_paths:
        assert "divine-secret-token" not in path.read_text(encoding="utf-8")
    assert "divine-secret-token" not in json.dumps(plan.redacted())


def test_codex_plan_uses_responses_wire_protocol(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: "codex.exe")
    plan = build_launch_plan(
        "codex",
        tmp_path,
        model="openai/gpt-test",
        forwarded=["exec", "hello"],
        server_url="http://127.0.0.1:8742",
        token="secret",
    )
    config = plan.config_paths[0].read_text(encoding="utf-8")
    assert 'wire_api = "responses"' in config
    assert 'base_url = "http://127.0.0.1:8742/v1"' in config
    assert 'env_key = "DIVINE_API_TOKEN"' in config


def test_claude_and_opencode_use_documented_environment_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(shutil, "which", lambda agent: f"{agent}.exe")
    claude = build_launch_plan(
        "claude",
        tmp_path / "claude-plan",
        model="anthropic/model",
        forwarded=[],
        server_url="http://127.0.0.1:8742",
        token="secret",
    )
    assert claude.environment["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:8742"
    assert claude.environment["CLAUDE_CONFIG_DIR"].startswith(str(tmp_path))

    opencode = build_launch_plan(
        "opencode",
        tmp_path / "opencode-plan",
        model="openai/model",
        forwarded=[],
        server_url="http://127.0.0.1:8742",
        token="secret",
    )
    config = json.loads(opencode.config_paths[0].read_text(encoding="utf-8"))
    assert config["provider"]["divine"]["options"]["baseURL"].endswith("/v1")
    assert opencode.environment["OPENCODE_CONFIG"] == str(opencode.config_paths[0])


def test_auto_model_is_rejected() -> None:
    with pytest.raises(ValueError, match="automatic routing"):
        wrappers._model("codex", "auto", None)


def test_wrapper_preserves_child_exit_code_and_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "child.json"
    helper = tmp_path / "fake_agent.py"
    helper.write_text(
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "Path(os.environ['FAKE_OUTPUT']).write_text(json.dumps(sys.argv[1:]))\n"
        "raise SystemExit(7)\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["divine-codex", "--no-start", "exec", "hello world"])
    monkeypatch.setattr(wrappers, "_model", lambda *_: "provider/model")
    monkeypatch.setattr(wrappers, "_server_details", lambda: ("http://127.0.0.1:8742", "secret"))
    monkeypatch.setattr(
        wrappers,
        "build_launch_plan",
        lambda *args, **kwargs: LaunchPlan(
            "codex",
            sys.executable,
            [str(helper), "exec", "hello world"],
            {"FAKE_OUTPUT": str(output)},
            "provider/model",
        ),
    )

    with pytest.raises(SystemExit) as exc:
        wrappers._run("codex")

    assert exc.value.code == 7
    assert json.loads(output.read_text(encoding="utf-8")) == ["exec", "hello world"]


def test_dry_run_redacts_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["divine-codex", "--dry-run", "exec", "hello"])
    monkeypatch.setattr(wrappers, "_model", lambda *_: "provider/model")
    monkeypatch.setattr(
        wrappers, "_server_details", lambda: ("http://127.0.0.1:8742", "divine-secret")
    )
    monkeypatch.setattr(shutil, "which", lambda _: sys.executable)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))

    with pytest.raises(SystemExit) as exc:
        wrappers._run("codex")

    assert exc.value.code == 0
    stdout = capsys.readouterr().out
    assert "divine-secret" not in stdout
    assert "[REDACTED]" in stdout


def test_missing_agent_fails_clearly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(FileNotFoundError, match="not installed"):
        build_launch_plan(
            "claude",
            tmp_path,
            model="provider/model",
            forwarded=[],
            server_url="http://127.0.0.1:8742",
            token="secret",
        )
