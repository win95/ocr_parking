#!/usr/bin/env bash
# Chuẩn bị máy SERVER (GPU) — chạy từ thư mục gốc repo
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== Smart Parking — SERVER setup =="
bash docs/setup/ubuntu-gpu.sh

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "WARN: nvidia-smi not found. Install NVIDIA driver before production inference."
fi

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip wheel
pip install -e ".[dev,inspector]"

mkdir -p data models logs logs/artifacts configs/slots
cp -n configs/deploy/server.yaml configs/deploy/server.local.yaml 2>/dev/null || true
echo "Edit configs/deploy/server.local.yaml — set rtsp://CLIENT_IP:8554/parking"
echo "Run: source .venv/bin/activate && python scripts/verify_gpu_ready.py"
echo "Run: SMART_PARKING_CONFIG=configs/deploy/server.local.yaml python -m smart_parking"
