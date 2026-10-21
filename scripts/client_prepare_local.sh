#!/usr/bin/env bash
# Chuẩn bị client không cần quyền root (trừ ffmpeg nếu chưa có)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p data logs tools /var/log/smart-parking 2>/dev/null || mkdir -p data logs tools

ENV="$ROOT/configs/deploy/client.local.env"
if [[ ! -f "$ENV" ]]; then
  cp configs/deploy/client-laptop.env.example "$ENV"
  sed -i "s|LAPTOP_LAN_IP=.*|LAPTOP_LAN_IP=$(hostname -I | awk '{print $1}')|" "$ENV" 2>/dev/null || true
fi

if [[ ! -x "$ROOT/tools/mediamtx" ]]; then
  echo "Tải MediaMTX..."
  curl -fsSL -o /tmp/mtx.tgz \
    "https://github.com/bluenviron/mediamtx/releases/download/v1.11.3/mediamtx_v1.11.3_linux_amd64.tar.gz"
  tar -xzf /tmp/mtx.tgz -C "$ROOT/tools" mediamtx
  chmod +x "$ROOT/tools/mediamtx"
fi

if command -v ffmpeg >/dev/null; then
  echo "OK: ffmpeg $(ffmpeg -version | head -1)"
elif [[ -x "$ROOT/tools/bin/ffmpeg" ]]; then
  echo "OK: ffmpeg (static) $(tools/bin/ffmpeg -version | head -1)"
else
  echo "Tải ffmpeg static (không cần sudo)..."
  mkdir -p "$ROOT/tools/bin"
  curl -fL --retry 3 -o /tmp/ffmpeg-static.tar.xz \
    "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-linux64-gpl.tar.xz"
  tar -xJf /tmp/ffmpeg-static.tar.xz -C /tmp
  cp /tmp/ffmpeg-master-latest-linux64-gpl/bin/ffmpeg /tmp/ffmpeg-master-latest-linux64-gpl/bin/ffprobe "$ROOT/tools/bin/"
  chmod +x "$ROOT/tools/bin/ffmpeg" "$ROOT/tools/bin/ffprobe"
  ln -sf "$ROOT/tools/bin/ffmpeg" "$HOME/.local/bin/ffmpeg"
  ln -sf "$ROOT/tools/bin/ffprobe" "$HOME/.local/bin/ffprobe"
  rm -rf /tmp/ffmpeg-static.tar.xz /tmp/ffmpeg-master-latest-linux64-gpl
  echo "OK: ffmpeg (static) $(ffmpeg -version | head -1)"
fi

if command -v v4l2-ctl >/dev/null; then
  v4l2-ctl --list-devices 2>/dev/null || true
else
  echo "THIẾU v4l-utils (v4l2-ctl) — cài cùng lệnh apt trên."
fi

echo ""
echo "IP LAN laptop (cho server): $(hostname -I | awk '{print $1}')"
echo "RTSP URL: rtsp://$(hostname -I | awk '{print $1}'):8554/parking"
echo "Chạy stream: export STREAM_ENV=$ENV && bash scripts/client_laptop_start.sh webcam"
