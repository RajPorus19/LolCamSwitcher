#!/bin/bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:99}"
export OBS_WEBSOCKET_PORT="${OBS_WEBSOCKET_PORT:-4455}"
export OBS_WEBSOCKET_PASSWORD="${OBS_WEBSOCKET_PASSWORD:-}"
export OBS_PROFILE="${OBS_PROFILE:-regie}"
export OBS_COLLECTION="${OBS_COLLECTION:-regie}"

echo "Starting Xvfb on ${DISPLAY}..."
Xvfb "${DISPLAY}" -screen 0 1920x1080x24 +extension GLX +render -noreset &
XVFB_PID=$!

sleep 2

python3 /configure-obs.py

echo "OBS WebSocket port: ${OBS_WEBSOCKET_PORT}"
echo "Profile: ${OBS_PROFILE} | Collection: ${OBS_COLLECTION}"
echo "RTMP sources for scenes PLAYER_A / PLAYER_B:"
echo "  rtmp://rtmp:1935/live/playerA"
echo "  rtmp://rtmp:1935/live/playerB"

if [ -n "${TWITCH_STREAM_KEY:-}" ]; then
  echo "Twitch stream key loaded from TWITCH_STREAM_KEY"
  if [ "${TWITCH_AUTO_START:-true}" = "true" ]; then
    echo "TWITCH_AUTO_START=true — will start streaming when OBS is ready"
  fi
else
  echo "Set TWITCH_STREAM_KEY in .env to configure Twitch output"
fi

# Run OBS in background so we can trigger StartStream via WebSocket
obs \
  --profile "${OBS_PROFILE}" \
  --collection "${OBS_COLLECTION}" \
  --minimize-to-tray 2>&1 &
OBS_PID=$!

python3 /wait-and-start-stream.py || echo "WARN: Twitch auto-start failed (OBS keeps running)" >&2

wait "${OBS_PID}"
