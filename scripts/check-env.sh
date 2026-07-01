#!/usr/bin/env bash
# Verify .env before docker compose up (run from repo root)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  echo "ERROR: .env missing. Run: cp .env.example .env"
  exit 1
fi

python3 - <<'PY'
import pathlib
import sys

path = pathlib.Path(".env")
values = {}
for line in path.read_text(encoding="utf-8-sig").splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    if line.startswith("export "):
        line = line[7:].strip()
    if "=" not in line:
        continue
    k, _, v = line.partition("=")
    values[k.strip()] = v.strip().strip('"').strip("'")

token = values.get("LOL_DIRECTOR_API_TOKEN", "")
bad = {"", "change-me-to-a-long-random-secret", "changeme"}
if token in bad:
    print("ERROR: LOL_DIRECTOR_API_TOKEN missing or placeholder in .env")
    if values:
        print("Keys found:", ", ".join(sorted(values.keys())))
    sys.exit(1)
print(f"OK: LOL_DIRECTOR_API_TOKEN set ({len(token)} chars)")
obs = values.get("OBS_ENABLED", "false").lower()
if obs in ("1", "true", "yes", "on"):
    print("INFO: OBS_ENABLED=true — use: docker compose --profile full up -d")
PY

docker compose config >/dev/null
echo "OK: docker compose config valid"
