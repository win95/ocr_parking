#!/usr/bin/env bash
# Chuẩn bị máy CLIENT (camera / stream RTSP)
# Usage: bash scripts/setup_client.sh [--role streamer|edge] [--install-app]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ROLE="streamer"
INSTALL_APP=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --role) ROLE="${2:-streamer}"; shift 2 ;;
    --install-app) INSTALL_APP=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "== Smart Parking — CLIENT setup (role=$ROLE) =="
sudo apt update
sudo apt install -y ffmpeg v4l-utils curl

mkdir -p data /var/log/smart-parking

if [[ "$ROLE" == "edge" ]] || [[ "$INSTALL_APP" == true ]]; then
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -U pip wheel
  pip install -e ".[dev,inspector]"
  mkdir -p logs configs/slots models
  echo "Edge mode: python -m smart_parking --config configs/deploy/edge.yaml"
else
  echo "Streamer mode: copy configs/deploy/client-stream.env.example → /etc/smart-parking/stream.env"
  echo "Start: bash scripts/run_rtsp_publish.sh /dev/video0"
fi
