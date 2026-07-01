"""Tests for .env token loading."""

import os
from pathlib import Path

from lol_cam_switcher.server.env_loader import apply_mounted_dotenv, parse_dotenv, resolve_api_token, resolve_env_bool


def test_parse_dotenv(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text(
        "# comment\nLOL_DIRECTOR_API_TOKEN=secret123\nREQUIRE_API_TOKEN=true\n",
        encoding="utf-8",
    )
    values = parse_dotenv(env)
    assert values["LOL_DIRECTOR_API_TOKEN"] == "secret123"


def test_resolve_from_file(tmp_path: Path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("LOL_DIRECTOR_API_TOKEN=my-token\n", encoding="utf-8")
    monkeypatch.delenv("LOL_DIRECTOR_API_TOKEN", raising=False)
    token, source = resolve_api_token(env_file=str(env))
    assert token == "my-token"
    assert source == f"file:{env}"


def test_resolve_prefers_env(monkeypatch):
    monkeypatch.setenv("LOL_DIRECTOR_API_TOKEN", "from-env")
    token, source = resolve_api_token(env_file="/nonexistent")
    assert token == "from-env"
    assert source == "env"


def test_apply_mounted_dotenv_overrides_stale_env(monkeypatch, tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text("OBS_ENABLED=true\nOBS_HOST=obs\n", encoding="utf-8")
    monkeypatch.setenv("OBS_ENABLED", "false")
    monkeypatch.setenv("OBS_HOST", "localhost")
    path = apply_mounted_dotenv(env_file=str(env))
    assert path == env
    assert os.environ["OBS_ENABLED"] == "true"
    assert os.environ["OBS_HOST"] == "obs"
    assert resolve_env_bool("OBS_ENABLED", False) is True


def test_resolve_env_bool_prefers_file_over_compose_false(monkeypatch, tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text("OBS_ENABLED=true\n", encoding="utf-8")
    monkeypatch.setenv("OBS_ENABLED", "false")
    assert resolve_env_bool("OBS_ENABLED", False, env_file=str(env)) is True


def test_resolve_file_when_env_empty(monkeypatch, tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text("LOL_DIRECTOR_API_TOKEN=file-token\n", encoding="utf-8")
    monkeypatch.setenv("LOL_DIRECTOR_API_TOKEN", "")
    token, source = resolve_api_token(env_file=str(env))
    assert token == "file-token"
    assert source == f"file:{env}"
