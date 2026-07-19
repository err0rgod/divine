"""Platform-appropriate paths for configuration and local runtime state."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import PlatformDirs


@dataclass(frozen=True, slots=True)
class DivinePaths:
    """All persistent paths used by Divine Router."""

    config_dir: Path
    data_dir: Path
    cache_dir: Path
    log_dir: Path

    @classmethod
    def discover(cls) -> DivinePaths:
        """Discover platform paths, honoring isolated per-process overrides."""
        dirs = PlatformDirs("divine-router", appauthor=False, roaming=True)
        config_dir = Path(os.environ.get("DIVINE_CONFIG_DIR", dirs.user_config_path)).expanduser()
        data_dir = Path(os.environ.get("DIVINE_DATA_DIR", dirs.user_data_path)).expanduser()
        cache_dir = Path(os.environ.get("DIVINE_CACHE_DIR", dirs.user_cache_path)).expanduser()
        log_dir = Path(os.environ.get("DIVINE_LOG_DIR", dirs.user_log_path)).expanduser()
        return cls(
            config_dir=config_dir.resolve(),
            data_dir=data_dir.resolve(),
            cache_dir=cache_dir.resolve(),
            log_dir=log_dir.resolve(),
        )

    @property
    def config_file(self) -> Path:
        return self.config_dir / "config.toml"

    @property
    def database_file(self) -> Path:
        return self.data_dir / "divine.db"

    @property
    def token_file(self) -> Path:
        return self.config_dir / "api-token"
