"""Server entry point."""

from __future__ import annotations

import argparse
import logging
import sys

import uvicorn

from lol_cam_switcher.server.app import create_app
from lol_cam_switcher.server.config import ServerConfig, _env_bool, app_config_from_env


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="LolCamSwitcher — regie server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8750)
    parser.add_argument(
        "--token",
        default="",
        help="API token (or set LOL_DIRECTOR_API_TOKEN env var)",
    )
    parser.add_argument(
        "--no-obs",
        action="store_true",
        help="Disable OBS connection (API-only mode)",
    )
    parser.add_argument(
        "--require-token",
        action="store_true",
        default=_env_bool("REQUIRE_API_TOKEN", False),
        help="Exit if LOL_DIRECTOR_API_TOKEN is not set",
    )
    args = parser.parse_args()

    obs_enabled = _env_bool("OBS_ENABLED", True)
    if args.no_obs:
        obs_enabled = False

    cfg = ServerConfig(
        host=args.host,
        port=args.port,
        api_token=args.token,
        obs_enabled=obs_enabled,
        require_token=args.require_token,
    )
    token = cfg.ensure_token()
    if not cfg.require_token:
        print(f"LolCamSwitcher Server — Bearer token: {token}")
    print(f"Clients must send: Authorization: Bearer <token>")

    app = create_app(server_config=cfg, app_config=app_config_from_env())
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
