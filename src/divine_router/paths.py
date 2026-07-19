"""Platform-appropriate paths for configuration and local runtime state."""

from __future__ import annotations

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
        dirs = PlatformDirs("divine-router", appauthor=False, roaming=True)
        return cls(
            config_dir=Path(dirs.user_config_path),
            data_dir=Path(dirs.user_data_path),
            cache_dir=Path(dirs.user_cache_path),
            log_dir=Path(dirs.user_log_path),
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
