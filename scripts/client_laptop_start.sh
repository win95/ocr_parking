#!/usr/bin/env bash
# Laptop client — B: khởi động MediaMTX + publish RTSP
# Usage:
#   bash scripts/client_laptop_start.sh webcam
#   bash scripts/client_laptop_start.sh video /path/to/file.mp4
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-webcam}"
INPUT="${2:-/dev/video0}"
ENV_FILE="${STREAM_ENV:-/etc/smart-parking/stream.env}"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

if ! command -v mediamtx >/dev/null 2>&1; then
  echo "Install MediaMTX first: sudo bash scripts/install_mediamtx_client.sh"
  exit 1
fi

if ! pgrep -x mediamtx >/dev/null 2>&1; then
  echo "Starting mediamtx in background..."
  mediamtx >/var/log/smart-parking/mediamtx.log 2>&1 &
  sleep 2
fi

case "$MODE" in
  webcam)
    DEVICE="${VIDEO_DEVICE:-$INPUT}"
    echo "Publishing webcam $DEVICE → rtsp://$(hostname -I | awk '{print $1}'):${RTSP_LISTEN:-8554}/${RTSP_PATH:-parking}"
    exec bash "$ROOT/scripts/run_rtsp_publish.sh" "$DEVICE"
    ;;
  video)
    if [[ ! -f "$INPUT" ]]; then
      echo "File not found: $INPUT"
      exit 1
    fi
    echo "Looping video $INPUT → RTSP"
    exec bash "$ROOT/scripts/run_rtsp_publish.sh" "$INPUT"
    ;;
  *)
    echo "Usage: $0 webcam|video [path]"
    exit 1
    ;;
esac
