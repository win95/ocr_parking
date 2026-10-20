#!/usr/bin/env python3
"""Roboflow dataset download and YOLO train helper (requires ROBOFLOW_API_KEY)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--version", type=int, default=1)
    parser.add_argument("--model", default="yolo11s.pt")
    parser.add_argument("--epochs", type=int, default=100)
    args = parser.parse_args()

    api_key = os.environ.get("ROBOFLOW_API_KEY")
    if not api_key:
        print("Set ROBOFLOW_API_KEY in .env", file=sys.stderr)
        return 1

    from roboflow import Roboflow

    rf = Roboflow(api_key=api_key)
    project = rf.workspace(args.workspace).project(args.project)
    dataset = project.version(args.version).download("yolov11")
    data_yaml = os.path.join(dataset.location, "data.yaml")
    cmd = [
        "yolo",
        "train",
        f"data={data_yaml}",
        f"model={args.model}",
        f"epochs={args.epochs}",
        "imgsz=640",
        "device=0",
    ]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
