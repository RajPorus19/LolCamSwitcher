#!/bin/sh
set -eu

if [ -z "${LOL_DIRECTOR_API_TOKEN:-}" ]; then
  echo "ERROR: LOL_DIRECTOR_API_TOKEN is empty inside the container." >&2
  echo "Fix: in .env next to docker-compose.yml, use exactly:" >&2
  echo "  LOL_DIRECTOR_API_TOKEN=your-secret-here" >&2
  echo "No spaces around '=', no 'export', one line." >&2
  echo "Then: docker compose up -d --force-recreate director" >&2
  echo "Verify on host: grep LOL_DIRECTOR_API_TOKEN .env" >&2
  exit 1
fi

exec python -m lol_cam_switcher.server
