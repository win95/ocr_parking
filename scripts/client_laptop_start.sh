#!/usr/bin/env bash
# Laptop client — B: khởi động MediaMTX + publish RTSP
# Usage:
#   bash scripts/client_laptop_start.sh webcam
#   bash scripts/client_laptop_start.sh video /path/to/file.mp4
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-webcam}"
INPUT="${2:-/dev/video0}"
ENV_FILE="${STREAM_ENV:-$ROOT/configs/deploy/client.local.env}"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"
MTX="${MEDIAMTX_BIN:-$ROOT/tools/mediamtx}"
MTX_CONF="${MEDIAMTX_CONF:-$ROOT/configs/deploy/mediamtx-client.yml}"
if [[ ! -x "$MTX" ]] && command -v mediamtx >/dev/null 2>&1; then
  MTX=mediamtx
fi
if [[ ! -x "$MTX" ]]; then
  echo "Chạy: bash scripts/client_prepare_local.sh"
  exit 1
fi

if ! pgrep -f "$MTX" >/dev/null 2>&1; then
  echo "Starting MediaMTX..."
  mkdir -p "$ROOT/logs"
  if [[ -f "$MTX_CONF" ]]; then
    "$MTX" "$MTX_CONF" >"$ROOT/logs/mediamtx.log" 2>&1 &
  else
    "$MTX" >"$ROOT/logs/mediamtx.log" 2>&1 &
  fi
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
