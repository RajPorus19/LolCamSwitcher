#!/usr/bin/env python3
"""CLI preflight — verify LOL_DIRECTOR_API_TOKEN is available."""

from __future__ import annotations

import sys
from pathlib import Path

from lol_cam_switcher.server.env_loader import (
    DEFAULT_ENV_FILE,
    PLACEHOLDER_TOKENS,
    apply_mounted_dotenv,
    parse_dotenv,
    resolve_api_token,
    resolve_env_bool,
)


def main() -> int:
    mounted = apply_mounted_dotenv()
    token, source = resolve_api_token()
    if "--print" in sys.argv:
        if not token:
            return 1
        sys.stdout.write(token)
        return 0

    if token:
        if source.startswith("file:"):
            print(f"OK: LOL_DIRECTOR_API_TOKEN from {source.removeprefix('file:')} ({len(token)} chars)")
        else:
            print(f"OK: LOL_DIRECTOR_API_TOKEN from environment ({len(token)} chars)")
        obs = resolve_env_bool("OBS_ENABLED", False)
        print(f"OK: OBS_ENABLED={obs}" + (f" (from {mounted})" if mounted else ""))
        return 0

    print("ERROR: LOL_DIRECTOR_API_TOKEN missing or invalid.", file=sys.stderr)
    env_path = Path(DEFAULT_ENV_FILE)
    if env_path.is_file():
        keys = sorted(parse_dotenv(env_path).keys())
        if "LOL_DIRECTOR_API_TOKEN" in keys:
            val = parse_dotenv(env_path).get("LOL_DIRECTOR_API_TOKEN", "")
            if val in PLACEHOLDER_TOKENS:
                print("LOL_DIRECTOR_API_TOKEN is empty or still the example placeholder.", file=sys.stderr)
        else:
            print(f"{env_path} has no LOL_DIRECTOR_API_TOKEN line.", file=sys.stderr)
            if keys:
                print(f"Keys found: {', '.join(keys)}", file=sys.stderr)
    else:
        print(f"{env_path} not found.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
