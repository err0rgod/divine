from __future__ import annotations

from pathlib import Path

import pytest
from textual.widgets import TabbedContent
from typer.testing import CliRunner

from divine_router.cli import app
from divine_router.tui import PAGES, DivineRouterTUI


@pytest.fixture
def isolated_cli_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for kind in ("CONFIG", "DATA", "CACHE", "LOG"):
        monkeypatch.setenv(f"DIVINE_{kind}_DIR", str(tmp_path / kind.lower()))
    return tmp_path


def test_doctor_initializes_isolated_configuration(isolated_cli_paths: Path) -> None:
    result = CliRunner().invoke(app, ["doctor"])
    assert result.exit_code == 0, result.output
    assert "config: valid" in result.output
    assert "enabled providers with credentials: 0" in result.output
    assert (isolated_cli_paths / "config" / "config.toml").exists()
    assert (isolated_cli_paths / "config" / "api-token").exists()


def test_provider_listing_and_toml_export(isolated_cli_paths: Path) -> None:
    runner = CliRunner()
    providers = runner.invoke(app, ["providers"])
    assert providers.exit_code == 0, providers.output
    assert "openai\tdisabled\tcompatible-unverified" in providers.output
    exported = runner.invoke(app, ["config", "export"])
    assert exported.exit_code == 0, exported.output
    assert "schema_version = 1" in exported.output
    assert "[[providers]]" in exported.output
    assert '"providers":' not in exported.output


def test_status_does_not_trust_a_stale_pid_file(isolated_cli_paths: Path) -> None:
    data_dir = isolated_cli_paths / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "server.pid").write_text('{"pid": 1, "created": 0}', encoding="utf-8")
    result = CliRunner().invoke(app, ["status"])
    assert result.exit_code == 1
    assert "stopped" in result.output


@pytest.mark.asyncio
async def test_tui_exposes_operations_pages() -> None:
    application = DivineRouterTUI()
    async with application.run_test() as pilot:
        tabs = application.query_one(TabbedContent)
        assert tabs.active == "dashboard"
        await pilot.press("d")
        assert tabs.active == "dashboard"
    assert len(PAGES) == 13
