#!/bin/bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:99}"
export OBS_WEBSOCKET_PORT="${OBS_WEBSOCKET_PORT:-4455}"
export OBS_WEBSOCKET_PASSWORD="${OBS_WEBSOCKET_PASSWORD:-}"

echo "Starting Xvfb on ${DISPLAY}..."
Xvfb "${DISPLAY}" -screen 0 1920x1080x24 +extension GLX +render -noreset &
XVFB_PID=$!

sleep 2

echo "OBS WebSocket port: ${OBS_WEBSOCKET_PORT}"
echo "Configure OBS scenes PLAYER_A, PLAYER_B, SPLIT with RTMP sources:"
echo "  rtmp://rtmp:1935/live/playerA"
echo "  rtmp://rtmp:1935/live/playerB"

# Run OBS — websocket v5 is built into OBS 28+
exec obs --profile regie --collection regie --minimize-to-tray 2>&1
