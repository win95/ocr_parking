#!/usr/bin/env python3
"""Export YOLO weights to ONNX and optionally TensorRT engine."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--out-dir", default="models")
    parser.add_argument("--half", action="store_true", help="FP16 engine via trtexec")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    from ultralytics import YOLO

    model = YOLO(args.model)
    onnx_path = out_dir / f"{Path(args.model).stem}.onnx"
    model.export(format="onnx", imgsz=args.imgsz, simplify=True)
    exported = Path(model.ckpt_path or args.model).with_suffix(".onnx")
    if exported.exists() and exported != onnx_path:
        shutil.move(str(exported), str(onnx_path))
    print(f"ONNX: {onnx_path}")

    if shutil.which("trtexec"):
        engine = out_dir / f"{Path(args.model).stem}.engine"
        cmd = [
            "trtexec",
            f"--onnx={onnx_path}",
            f"--saveEngine={engine}",
        ]
        if args.half:
            cmd.append("--fp16")
        subprocess.run(cmd, check=False)
        print(f"Engine: {engine}")
    else:
        print("trtexec not found; skip engine build")


if __name__ == "__main__":
    main()
