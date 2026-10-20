#!/usr/bin/env bash
# Safe apt-only bootstrap. Driver/CUDA/TensorRT: follow docs/setup/ubuntu-gpu.md
set -euo pipefail
sudo apt update
sudo apt install -y build-essential git curl wget ffmpeg v4l-utils \
  libgl1 libglib2.0-0 libgtk-3-0 pkg-config
echo "Done. Install NVIDIA driver separately and reboot."
