"""Server configuration."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field


def _default_token() -> str:
    return os.environ.get("LOL_DIRECTOR_API_TOKEN", "")


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8750
    api_token: str = field(default_factory=_default_token)
    cors_origins: list[str] = field(default_factory=lambda: ["*"])

    def ensure_token(self) -> str:
        if not self.api_token:
            self.api_token = secrets.token_urlsafe(32)
        return self.api_token
