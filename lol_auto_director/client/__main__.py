"""Client agent entry point."""

from __future__ import annotations

import logging
import sys


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    from lol_auto_director.client.gui import run_client

    return run_client()


if __name__ == "__main__":
    sys.exit(main())
