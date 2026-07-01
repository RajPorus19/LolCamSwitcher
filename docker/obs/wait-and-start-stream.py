#!/usr/bin/env python3
"""Wait for OBS WebSocket and optionally start Twitch streaming."""

from __future__ import annotations

import os
import sys
import time


def _env_bool(key: str, default: bool = True) -> bool:
    val = os.environ.get(key, "").lower()
    if val in ("1", "true", "yes", "on"):
        return True
    if val in ("0", "false", "no", "off"):
        return False
    return default


def should_auto_start() -> bool:
    if not _env_bool("TWITCH_AUTO_START", True):
        print("TWITCH_AUTO_START=false — skipping stream start")
        return False
    if not os.environ.get("TWITCH_STREAM_KEY", "").strip():
        print("TWITCH_STREAM_KEY not set — skipping stream start", file=sys.stderr)
        return False
    return True


def main() -> int:
    if not should_auto_start():
        return 0

    try:
        import obsws_python as obs
    except ImportError:
        print("obsws-python not installed", file=sys.stderr)
        return 1

    host = os.environ.get("OBS_WEBSOCKET_HOST", "127.0.0.1")
    port = int(os.environ.get("OBS_WEBSOCKET_PORT", "4455"))
    password = os.environ.get("OBS_WEBSOCKET_PASSWORD", "")
    max_attempts = int(os.environ.get("TWITCH_AUTO_START_RETRIES", "45"))

    for attempt in range(1, max_attempts + 1):
        try:
            client = obs.ReqClient(
                host=host,
                port=port,
                password=password,
                timeout=5,
            )
            status = client.get_stream_status()
            if getattr(status, "output_active", False):
                print("Twitch stream already active")
                return 0
            client.start_stream()
            # Confirm stream actually started
            time.sleep(2)
            status = client.get_stream_status()
            if getattr(status, "output_active", False):
                print("Twitch stream started (OBS WebSocket StartStream)")
                return 0
            print(
                f"StartStream sent but output not active yet (attempt {attempt}/{max_attempts})",
                file=sys.stderr,
            )
        except Exception as exc:
            print(
                f"Waiting for OBS WebSocket ({attempt}/{max_attempts}): {exc}",
                file=sys.stderr,
            )
        time.sleep(2)

    print("ERROR: failed to start Twitch stream after OBS startup", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
