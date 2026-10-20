#!/usr/bin/env bash
# Server — chạy app với config RTSP (sau khi sửa server.local.yaml)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CFG="${SMART_PARKING_CONFIG:-configs/deploy/server.local.yaml}"

if [[ ! -f "$CFG" ]]; then
  echo "Create $CFG from configs/deploy/server-rtsp.yaml and set LAPTOP_IP"
  exit 1
fi

if grep -q LAPTOP_IP "$CFG"; then
  echo "Replace LAPTOP_IP in $CFG with laptop LAN address"
  exit 1
fi

source .venv/bin/activate
RTSP_URL="$(python -c "import yaml; print(yaml.safe_load(open('$CFG'))['source'])")"
echo "Probing $RTSP_URL ..."
ffprobe -rtsp_transport tcp -v error -select_streams v:0 -show_entries stream=codec_name,width,height -of csv=p=0 "$RTSP_URL" || {
  echo "Cannot reach RTSP. Start laptop client first."
  exit 1
}
exec python -m smart_parking --config "$CFG"
