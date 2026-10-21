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
  mkdir -p "$ROOT/tools/bin" "$HOME/.local/bin"
  curl -fL --retry 3 -o /tmp/ffmpeg-static.tar.xz \
    "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-linux64-gpl.tar.xz"
  tar -xJf /tmp/ffmpeg-static.tar.xz -C /tmp
  for bin in ffmpeg ffprobe ffplay; do
    cp "/tmp/ffmpeg-master-latest-linux64-gpl/bin/$bin" "$ROOT/tools/bin/"
    chmod +x "$ROOT/tools/bin/$bin"
    ln -sf "$ROOT/tools/bin/$bin" "$HOME/.local/bin/$bin"
  done
  rm -rf /tmp/ffmpeg-static.tar.xz /tmp/ffmpeg-master-latest-linux64-gpl
  echo "OK: ffmpeg (static) $(ffmpeg -version | head -1)"
fi

# ffprobe / ffplay — dùng để kiểm tra stream RTSP (docs: SCENARIO_B_LAPTOP_CLIENT.md)
for tool in ffprobe ffplay; do
  if command -v "$tool" >/dev/null; then
    echo "OK: $tool $("$tool" -version | head -1 | sed 's/.*version //;s/ .*//')"
  elif [[ -x "$ROOT/tools/bin/$tool" ]]; then
    echo "OK: $tool (static) $("$ROOT/tools/bin/$tool" -version | head -1 | sed 's/.*version //;s/ .*//')"
  else
    echo "THIẾU $tool — cài: sudo apt install ffmpeg"
  fi
done

if command -v v4l2-ctl >/dev/null; then
  v4l2-ctl --list-devices 2>/dev/null || true
else
  echo "THIẾU v4l-utils (v4l2-ctl) — cài cùng lệnh apt trên."
fi

echo ""
echo "IP LAN laptop (cho server): $(hostname -I | awk '{print $1}')"
echo "RTSP URL: rtsp://$(hostname -I | awk '{print $1}'):8554/parking"
echo "Chạy stream: export STREAM_ENV=$ENV && bash scripts/client_laptop_start.sh webcam"
