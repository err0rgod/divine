"""Atomic TOML configuration IO with validation, migration, and backups."""

from __future__ import annotations

import os
import shutil
import tempfile
import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from divine_router.config.models import DivineConfig
from divine_router.constants import SCHEMA_VERSION


class ConfigManager:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()

    def load(self) -> DivineConfig:
        if not self.path.exists():
            return DivineConfig()
        raw = tomllib.loads(self.path.read_text(encoding="utf-8"))
        migrated = self.migrate(raw)
        return DivineConfig.model_validate(migrated)

    def save(self, config: DivineConfig) -> Path | None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        backup: Path | None = None
        if self.path.exists():
            backup_dir = self.path.parent / ".backups"
            backup_dir.mkdir(exist_ok=True)
            backup = backup_dir / f"{self.path.name}.bak"
            shutil.copy2(self.path, backup)
        payload = self.dumps(config)
        handle, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.path)
        finally:
            temporary.unlink(missing_ok=True)
        return backup

    @staticmethod
    def dumps(config: DivineConfig) -> str:
        """Serialize validated configuration without resolving credential values."""
        return tomli_w.dumps(config.model_dump(mode="json", exclude_none=True))

    @staticmethod
    def migrate(raw: dict[str, Any]) -> dict[str, Any]:
        version = int(raw.get("schema_version", 1))
        if version > SCHEMA_VERSION:
            raise ValueError(f"unsupported future configuration schema {version}")
        migrated = dict(raw)
        migrated["schema_version"] = SCHEMA_VERSION
        return migrated
