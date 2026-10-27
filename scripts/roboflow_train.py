#!/usr/bin/env python3
"""Roboflow dataset download and YOLO train helper (requires ROBOFLOW_API_KEY)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _train_yolo(data_yaml: str, model: str, epochs: int) -> int:
    cmd = [
        "yolo",
        "train",
        f"data={data_yaml}",
        f"model={model}",
        f"epochs={epochs}",
        "imgsz=640",
        "device=0",
    ]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--version", type=int, default=1)
    parser.add_argument("--model", default="yolo11s.pt")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--config", default=None, help="Optional pipeline YAML to log")
    parser.add_argument("--mlflow", action="store_true", help="Log run to MLflow")
    parser.add_argument("--experiment", default=None)
    parser.add_argument("--run-name", default=None)
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

    if not args.mlflow:
        return _train_yolo(data_yaml, args.model, args.epochs)

    from smart_parking.experiment.mlflow_run import DatasetRef, ExperimentRun, log_model_info

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_name = args.run_name or f"train-{args.project}-v{args.version}-{stamp}"
    dataset_name = f"{args.workspace}/{args.project}"

    with ExperimentRun(
        run_name=run_name,
        experiment_name=args.experiment,
        config_path=Path(args.config) if args.config else None,
        dataset=DatasetRef(dataset_name, dataset_version=str(args.version), uri=dataset.location),
        model_version=args.model,
        tags={"task": "yolo_train"},
    ) as run:
        log_model_info(args.model, "ultralytics", {"epochs": str(args.epochs)})
        run.log_artifact(data_yaml, artifact_path="dataset")
        code = _train_yolo(data_yaml, args.model, args.epochs)
        run.log_metrics({"train_exit_code": float(code)})
        return code


if __name__ == "__main__":
    raise SystemExit(main())
