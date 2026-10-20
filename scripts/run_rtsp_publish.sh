#!/usr/bin/env bash
# Phát RTSP từ webcam hoặc file video (chạy trên CLIENT)
set -euo pipefail

INPUT="${1:-/dev/video0}"
ENV_FILE="${STREAM_ENV:-/etc/smart-parking/stream.env}"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

PORT="${RTSP_LISTEN:-8554}"
PATH_NAME="${RTSP_PATH:-parking}"
SIZE="${VIDEO_SIZE:-1280x720}"
FPS="${VIDEO_FPS:-15}"
# MediaMTX (hoặc RTSP server) phải chạy trước — xem install_mediamtx_client.sh
RTSP_HOST="${RTSP_HOST:-127.0.0.1}"
URL="rtsp://${RTSP_HOST}:${PORT}/${PATH_NAME}"

if [[ -f "$INPUT" ]] && [[ "$INPUT" == *.mp4 ]]; then
  exec ffmpeg -re -stream_loop -1 -i "$INPUT" \
    -c:v libx264 -preset ultrafast -tune zerolatency \
    -f rtsp -rtsp_transport tcp "$URL"
fi

exec ffmpeg -f v4l2 -framerate "$FPS" -video_size "$SIZE" -i "$INPUT" \
  -c:v libx264 -preset ultrafast -tune zerolatency \
  -f rtsp -rtsp_transport tcp "$URL"
