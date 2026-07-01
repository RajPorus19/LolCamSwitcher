"""Server configuration."""

from __future__ import annotations

import os
import secrets
import sys
from dataclasses import dataclass, field
from pathlib import Path

from lol_cam_switcher.config import AppConfig
from lol_cam_switcher.server.env_loader import (
    DEFAULT_ENV_FILE,
    PLACEHOLDER_TOKENS,
    parse_dotenv,
    resolve_api_token,
)


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key, "").lower()
    if val in ("1", "true", "yes", "on"):
        return True
    if val in ("0", "false", "no", "off"):
        return False
    return default


def _default_token() -> str:
    token, _ = resolve_api_token()
    return token


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8750
    api_token: str = field(default_factory=_default_token)
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    obs_enabled: bool = field(default_factory=lambda: _env_bool("OBS_ENABLED", True))
    require_token: bool = field(default_factory=lambda: _env_bool("REQUIRE_API_TOKEN", False))

    def ensure_token(self) -> str:
        token, source = resolve_api_token()
        if token and token not in PLACEHOLDER_TOKENS:
            self.api_token = token
            if source.startswith("file:"):
                print(f"Loaded LOL_DIRECTOR_API_TOKEN from {source.removeprefix('file:')} ({len(token)} chars)")
            return token

        if self.require_token:
            env_path = Path(os.environ.get("LOL_DIRECTOR_ENV_FILE", DEFAULT_ENV_FILE))
            print(
                "ERROR: LOL_DIRECTOR_API_TOKEN is missing or invalid.",
                file=sys.stderr,
            )
            print(
                "Set it in .env next to docker-compose.yml, then rebuild:",
                file=sys.stderr,
            )
            print(
                "  LOL_DIRECTOR_API_TOKEN=$(openssl rand -hex 32)",
                file=sys.stderr,
            )
            print(
                "  docker compose build --no-cache director && docker compose up -d --force-recreate director",
                file=sys.stderr,
            )
            if env_path.is_file():
                keys = sorted(parse_dotenv(env_path).keys())
                if "LOL_DIRECTOR_API_TOKEN" in keys:
                    print(
                        "Found LOL_DIRECTOR_API_TOKEN in mounted .env but value is empty or placeholder.",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"Mounted {env_path} but LOL_DIRECTOR_API_TOKEN line not found.",
                        file=sys.stderr,
                    )
                    if keys:
                        print(f"Keys in .env: {', '.join(keys[:12])}", file=sys.stderr)
            else:
                print(
                    f"Mounted env file not found at {env_path} — pull latest compose and recreate container.",
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
        debug_mode=_env_bool("DEBUG_MODE", False),
        split_screen_enabled=_env_bool("SPLIT_SCREEN_ENABLED", False),
        riot_poll_interval_ms=int(os.environ.get("RIOT_POLL_INTERVAL_MS", "500")),
    )
