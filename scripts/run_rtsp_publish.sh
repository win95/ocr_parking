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
# GOP = khoảng cách keyframe. Nhỏ → client mới kết nối có hình nhanh.
# Mặc định 2 giây (2*FPS). Ví dụ GOP=30 @15fps.
GOP="${VIDEO_GOP:-$((FPS * 2))}"

# Tìm ffmpeg: FFMPEG_BIN > PATH > tools/bin (bản static không cần sudo)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -n "${FFMPEG_BIN:-}" ]]; then
  FFMPEG="$FFMPEG_BIN"
elif command -v ffmpeg >/dev/null 2>&1; then
  FFMPEG="$(command -v ffmpeg)"
elif [[ -x "$ROOT/tools/bin/ffmpeg" ]]; then
  FFMPEG="$ROOT/tools/bin/ffmpeg"
else
  echo "ERROR: ffmpeg not found. Cài: sudo apt install ffmpeg  hoặc  bash scripts/client_prepare_local.sh" >&2
  exit 127
fi
# MediaMTX (hoặc RTSP server) phải chạy trước — xem install_mediamtx_client.sh
RTSP_HOST="${RTSP_HOST:-127.0.0.1}"
URL="rtsp://${RTSP_HOST}:${PORT}/${PATH_NAME}"

if [[ -f "$INPUT" ]] && [[ "$INPUT" == *.mp4 ]]; then
  exec "$FFMPEG" -re -stream_loop -1 -i "$INPUT" \
    -c:v libx264 -preset ultrafast -tune zerolatency \
    -pix_fmt yuv420p -g "$GOP" -keyint_min "$GOP" -sc_threshold 0 \
    -f rtsp -rtsp_transport tcp "$URL"
fi

exec "$FFMPEG" -f v4l2 -framerate "$FPS" -video_size "$SIZE" -i "$INPUT" \
  -c:v libx264 -preset ultrafast -tune zerolatency \
  -pix_fmt yuv420p -g "$GOP" -keyint_min "$GOP" -sc_threshold 0 \
  -f rtsp -rtsp_transport tcp "$URL"
