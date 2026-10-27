#!/usr/bin/env bash
# Server — chạy app với config RTSP (mặc định server.detr.yaml)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CFG="${SMART_PARKING_CONFIG:-configs/deploy/server.detr.yaml}"

if [[ ! -f "$CFG" ]]; then
  echo "Không thấy $CFG — tạo bằng: bash scripts/setup_server.sh --rtsp rtsp://<LAPTOP_IP>:8554/parking"
  exit 1
fi

if grep -qE "LAPTOP_IP|CLIENT_IP" "$CFG"; then
  echo "Sửa source trong $CFG thành IP LAN của laptop (hoặc dùng --rtsp khi setup)"
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
