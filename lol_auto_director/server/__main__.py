"""Server entry point."""

from __future__ import annotations

import argparse
import logging
import sys

import uvicorn

from lol_auto_director.server.app import create_app
from lol_auto_director.server.config import ServerConfig


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="LoL Auto Director — regie server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8750)
    parser.add_argument(
        "--token",
        default="",
        help="API token (or set LOL_DIRECTOR_API_TOKEN env var)",
    )
    args = parser.parse_args()

    cfg = ServerConfig(host=args.host, port=args.port, api_token=args.token)
    token = cfg.ensure_token()
    print(f"LoL Auto Director Server — Bearer token: {token}")
    print(f"Clients must send: Authorization: Bearer {token}")

    app = create_app(server_config=cfg)
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
