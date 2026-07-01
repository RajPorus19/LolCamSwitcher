#!/usr/bin/env python3
"""Apply OBS profile settings from environment before startup."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

BUNDLE = Path("/opt/obs-bundle")
OBS_CONFIG = Path.home() / ".config" / "obs-studio"
PROFILE = os.environ.get("OBS_PROFILE", "regie")
COLLECTION = os.environ.get("OBS_COLLECTION", PROFILE)


def _write_service_json(profile_dir: Path) -> None:
    key = os.environ.get("TWITCH_STREAM_KEY", "").strip()
    if not key:
        print(
            "TWITCH_STREAM_KEY not set — stream Twitch à configurer manuellement dans OBS",
            file=sys.stderr,
        )
        return

    service = os.environ.get("TWITCH_SERVICE", "Twitch").strip() or "Twitch"
    server = os.environ.get("TWITCH_SERVER", "").strip()

    payload = {
        "type": "rtmp_common",
        "settings": {
            "service": service,
            "server": server,
            "key": key,
            "bwtest": False,
        },
    }
    (profile_dir / "service.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    if server:
        print(f"OBS stream configured: service={service}, server={server}")
    else:
        print(f"OBS stream configured: service={service} (ingest auto)")


def main() -> int:
    profile_dir = OBS_CONFIG / "basic" / "profiles" / PROFILE
    scenes_dir = OBS_CONFIG / "basic" / "scenes"
    profile_dir.mkdir(parents=True, exist_ok=True)
    scenes_dir.mkdir(parents=True, exist_ok=True)

    bundled_basic = BUNDLE / "basic.ini"
    if bundled_basic.is_file():
        shutil.copy(bundled_basic, profile_dir / "basic.ini")

    bundled_scene = BUNDLE / f"{COLLECTION}.json"
    if bundled_scene.is_file():
        shutil.copy(bundled_scene, scenes_dir / f"{COLLECTION}.json")

    _write_service_json(profile_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
