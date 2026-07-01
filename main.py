"""LoL Auto Director — entry point."""

import logging
import sys


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    from lol_auto_director.gui.app import run_app

    return run_app()


if __name__ == "__main__":
    sys.exit(main())
