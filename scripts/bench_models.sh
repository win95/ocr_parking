#!/usr/bin/env bash
# Benchmark all approved models in config (requires MLFLOW_TRACKING_URI).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CONFIG="${1:-configs/modes/benchmark.yaml}"
SECONDS="${BENCH_SECONDS:-30}"
source .venv/bin/activate 2>/dev/null || true
python scripts/benchmark_fps.py --config "$CONFIG" --seconds "$SECONDS" --mlflow \
  --dataset parking_lot --dataset-version v1 --run-name "detector-$(date +%Y%m%d%H%M)"
