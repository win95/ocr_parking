#!/usr/bin/env bash
# Cài MediaMTX (RTSP server) trên client — cần trước khi run_rtsp_publish.sh
set -euo pipefail
VER="${MEDIAMTX_VER:-v1.11.3}"
ARCH="linux_amd64"
URL="https://github.com/bluenviron/mediamtx/releases/download/${VER}/mediamtx_${VER}_${ARCH}.tar.gz"
TMP="$(mktemp -d)"
curl -fsSL "$URL" -o "$TMP/mtx.tgz"
sudo tar -xzf "$TMP/mtx.tgz" -C /usr/local/bin mediamtx
rm -rf "$TMP"
echo "Installed: mediamtx $(/usr/local/bin/mediamtx --version 2>/dev/null || true)"
echo "Run: mediamtx &   # listens :8554 by default"
