"""Server configuration."""

from __future__ import annotations

import os
import secrets
import sys
from dataclasses import dataclass, field

from lol_auto_director.config import AppConfig


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key, "").lower()
    if val in ("1", "true", "yes", "on"):
        return True
    if val in ("0", "false", "no", "off"):
        return False
    return default


def _default_token() -> str:
    return os.environ.get("LOL_DIRECTOR_API_TOKEN", "")


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8750
    api_token: str = field(default_factory=_default_token)
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    obs_enabled: bool = field(default_factory=lambda: _env_bool("OBS_ENABLED", True))
    require_token: bool = field(default_factory=lambda: _env_bool("REQUIRE_API_TOKEN", False))

    def ensure_token(self) -> str:
        if self.api_token:
            return self.api_token
        if self.require_token:
            print(
                "ERROR: LOL_DIRECTOR_API_TOKEN is required (set in .env)",
                file=sys.stderr,
            )
            sys.exit(1)
        self.api_token = secrets.token_urlsafe(32)
        return self.api_token


def app_config_from_env() -> AppConfig:
    """Build AppConfig from environment variables (Docker / Linux server)."""
    return AppConfig(
        obs_host=os.environ.get("OBS_HOST", "localhost"),
        obs_port=int(os.environ.get("OBS_PORT", "4455")),
        obs_password=os.environ.get("OBS_PASSWORD", ""),
        logs_dir=os.environ.get("LOGS_DIR", ""),
        auto_mode=_env_bool("AUTO_MODE", True),
        riot_poll_interval_ms=int(os.environ.get("RIOT_POLL_INTERVAL_MS", "500")),
    )
