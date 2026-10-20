#!/usr/bin/env bash
# Dev install: venv + editable package. Install PyTorch CUDA separately if needed.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip wheel
pip install -e ".[dev]"
if command -v nvidia-smi >/dev/null 2>&1; then
  echo "GPU detected. Install PyTorch with CUDA from https://pytorch.org then: pip install -r requirements-gpu.txt"
else
  echo "No nvidia-smi. CPU-only PyTorch is enough for unit tests."
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
  pip install -r requirements-gpu.txt
fi
python scripts/verify_gpu_ready.py
