"""Load secrets from process env and optional mounted .env file."""

from __future__ import annotations

import os
import pathlib

PLACEHOLDER_TOKENS = frozenset(
    {
        "",
        "change-me-to-a-long-random-secret",
        "changeme",
    }
)

DEFAULT_ENV_FILE = "/config/.env"


def normalize(value: str) -> str:
    return value.strip().strip('"').strip("'")


def parse_dotenv(path: pathlib.Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    text = path.read_text(encoding="utf-8-sig")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = normalize(value)
    return values


_TRUTHY = frozenset({"1", "true", "yes", "on"})
_FALSY = frozenset({"0", "false", "no", "off"})


def _parse_bool_str(value: str) -> bool | None:
    v = normalize(value).lower()
    if v in _TRUTHY:
        return True
    if v in _FALSY:
        return False
    return None


def resolve_env_bool(key: str, default: bool = False, *, env_file: str | None = None) -> bool:
    """
    Parse a boolean setting. Prefer mounted .env over process env when the file
    has an explicit value — Compose `environment:` overrides can force false
    even when .env says true (same class of bug as LOL_DIRECTOR_API_TOKEN).
    """
    path = pathlib.Path(env_file or os.environ.get("LOL_DIRECTOR_ENV_FILE", DEFAULT_ENV_FILE))
    file_values = parse_dotenv(path) if path.is_file() else {}

    file_bool = _parse_bool_str(file_values.get(key, ""))
    if file_bool is not None:
        return file_bool

    env_bool = _parse_bool_str(os.environ.get(key, ""))
    if env_bool is not None:
        return env_bool

    return default


def resolve_api_token(
    *,
    env_file: str | None = None,
) -> tuple[str, str]:
    """
    Return (token, source) where source is 'env', 'file', or '' if not found.

    Prefer mounted .env file when process env is empty (Docker Compose may inject
    an empty LOL_DIRECTOR_API_TOKEN that overrides env_file).
    """
    from_env = normalize(os.environ.get("LOL_DIRECTOR_API_TOKEN", ""))
    if from_env not in PLACEHOLDER_TOKENS:
        return from_env, "env"

    path = pathlib.Path(env_file or os.environ.get("LOL_DIRECTOR_ENV_FILE", DEFAULT_ENV_FILE))
    file_values = parse_dotenv(path)
    from_file = normalize(file_values.get("LOL_DIRECTOR_API_TOKEN", ""))
    if from_file not in PLACEHOLDER_TOKENS:
        return from_file, f"file:{path}"

    return "", ""
