#!/usr/bin/env python3
"""One-page GPU readiness report."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unavailable"


def main() -> int:
    print("=== Smart Parking GPU Readiness ===\n")
    print("nvidia-smi:", _run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"]))

    try:
        import torch

        print("torch:", torch.__version__)
        print("cuda available:", torch.cuda.is_available())
        if torch.cuda.is_available():
            print("device:", torch.cuda.get_device_name(0))
    except ImportError:
        print("torch: not installed")

    try:
        import cv2

        print("opencv:", cv2.__version__)
    except ImportError:
        print("opencv: not installed")

    try:
        import ultralytics

        print("ultralytics:", ultralytics.__version__)
    except ImportError:
        print("ultralytics: not installed")

    print("trtexec:", shutil.which("trtexec") or "not in PATH")

    free_gb = shutil.disk_usage(Path(".").resolve()).free / (1024**3)
    print(f"disk free: {free_gb:.1f} GB")
    data = Path("data")
    models = Path("models")
    data.mkdir(exist_ok=True)
    models.mkdir(exist_ok=True)
    print("data/ and models/ OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
