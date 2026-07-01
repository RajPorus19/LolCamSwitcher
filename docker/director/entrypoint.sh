#!/bin/sh
set -eu

python3 /load-env.py

exec python -m lol_cam_switcher.server
