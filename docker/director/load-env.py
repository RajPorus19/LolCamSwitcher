#!/usr/bin/env python3
"""Load LOL_DIRECTOR_API_TOKEN from container env or mounted .env file."""

from __future__ import annotations

import os
import pathlib
import sys

PLACEHOLDERS = frozenset({"", "change-me-to-a-long-random-secret", "changeme"})
ENV_PATH = pathlib.Path("/config/.env")


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
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def normalize(token: str) -> str:
    return token.strip().strip('"').strip("'")


def main() -> int:
    token = normalize(os.environ.get("LOL_DIRECTOR_API_TOKEN", ""))
    if token not in PLACEHOLDERS:
        os.environ["LOL_DIRECTOR_API_TOKEN"] = token
        return 0

    file_values = parse_dotenv(ENV_PATH)
    token = normalize(file_values.get("LOL_DIRECTOR_API_TOKEN", ""))
    if token not in PLACEHOLDERS:
        os.environ["LOL_DIRECTOR_API_TOKEN"] = token
        print(f"Loaded LOL_DIRECTOR_API_TOKEN from {ENV_PATH} ({len(token)} chars)")
        return 0

    print("ERROR: LOL_DIRECTOR_API_TOKEN missing or still the example placeholder.", file=sys.stderr)
    print("Edit .env in the project root (next to docker-compose.yml):", file=sys.stderr)
    print("  LOL_DIRECTOR_API_TOKEN=$(openssl rand -hex 32)", file=sys.stderr)
    print("One line, no spaces around '=', no 'export'.", file=sys.stderr)
    if ENV_PATH.is_file():
        keys = sorted(file_values.keys())
        preview = ", ".join(keys[:12])
        if "LOL_DIRECTOR_API_TOKEN" not in file_values:
            print(f"/config/.env mounted but LOL_DIRECTOR_API_TOKEN line not found.", file=sys.stderr)
            if keys:
                print(f"Keys seen in .env: {preview}", file=sys.stderr)
        else:
            print("LOL_DIRECTOR_API_TOKEN line exists but value is empty or placeholder.", file=sys.stderr)
    else:
        print(f"{ENV_PATH} not found — run: docker compose up -d --build --force-recreate director", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
