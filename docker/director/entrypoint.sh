#!/bin/sh
set -eu
python /load-env.py || exit 1
exec python -m lol_cam_switcher.server
