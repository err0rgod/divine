from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from divine_router.config.manager import ConfigManager
from divine_router.config.models import CredentialReference, DivineConfig, ServerConfig
from divine_router.models.canonical import CanonicalContent, ContentKind, TokenUsage
from divine_router.paths import DivinePaths
from divine_router.security.redaction import REDACTED, redact_mapping, redact_text, redact_url


def test_remote_binding_requires_explicit_opt_in() -> None:
    with pytest.raises(ValidationError):
        ServerConfig(host="0.0.0.0")
    assert ServerConfig(host="0.0.0.0", allow_remote_bind=True).allow_remote_bind


def test_credential_reference_requires_a_source() -> None:
    with pytest.raises(ValidationError):
        CredentialReference()


def test_canonical_content_is_validated() -> None:
    with pytest.raises(ValidationError):
        CanonicalContent(kind=ContentKind.TEXT)
    assert CanonicalContent(kind=ContentKind.TEXT, text="hello").text == "hello"


def test_usage_total() -> None:
    assert TokenUsage(input_tokens=3, output_tokens=2).total_tokens == 5


def test_redaction_covers_headers_text_and_urls() -> None:
    assert redact_mapping({"Authorization": "Bearer abc", "safe": "ok"}) == {
        "Authorization": REDACTED,
        "safe": "ok",
    }
    assert "secret-value" not in redact_text("token=secret-value", ("secret-value",))
    assert "abc" not in redact_url("https://example.test/hook?token=abc&safe=yes")


def test_config_round_trip_and_backup(tmp_path: Path) -> None:
    manager = ConfigManager(tmp_path / "config.toml")
    config = DivineConfig(aliases={"default": ["local/test"]})
    assert manager.save(config) is None
    assert manager.load() == config
    backup = manager.save(config)
    assert backup is not None and backup.exists()


def test_future_config_schema_is_rejected() -> None:
    with pytest.raises(ValueError, match="future"):
        ConfigManager.migrate({"schema_version": 999})


def test_platform_paths_allow_isolated_environment_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for kind in ("CONFIG", "DATA", "CACHE", "LOG"):
        monkeypatch.setenv(f"DIVINE_{kind}_DIR", str(tmp_path / kind.lower()))
    paths = DivinePaths.discover()
    assert paths.config_dir == (tmp_path / "config").resolve()
    assert paths.database_file == (tmp_path / "data" / "divine.db").resolve()
    assert paths.cache_dir == (tmp_path / "cache").resolve()
    assert paths.log_dir == (tmp_path / "log").resolve()
