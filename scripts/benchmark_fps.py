#!/usr/bin/env python3
"""Benchmark inference latency."""

from __future__ import annotations

import argparse
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from smart_parking.config import load_config
from smart_parking.detection.tensorrt_runner import create_detector
from smart_parking.ingest import FrameLoop, parse_source


def _run_benchmark(cfg_path: str, seconds: float) -> dict[str, float]:
    cfg = load_config(cfg_path)
    detector = create_detector(cfg.detection)
    source = parse_source(cfg.source)
    source.open()
    loop = FrameLoop(source, max_queue=1)

    latencies: list[float] = []
    end = time.perf_counter() + seconds
    warmup = 50
    idx = 0

    try:
        for ctx in loop:
            if time.perf_counter() > end:
                break
            t0 = time.perf_counter()
            detector.detect(ctx.image)
            dt = (time.perf_counter() - t0) * 1000.0
            idx += 1
            if idx > warmup:
                latencies.append(dt)
    finally:
        source.close()

    if not latencies:
        return {}
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    mean = statistics.mean(latencies)
    fps = 1000.0 / mean if mean > 0 else 0.0
    return {
        "samples": float(len(latencies)),
        "latency_mean_ms": mean,
        "latency_p50_ms": p50,
        "latency_p95_ms": p95,
        "fps": fps,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--mlflow", action="store_true", help="Log run to MLflow")
    parser.add_argument("--experiment", default=None, help="MLflow experiment name")
    parser.add_argument("--run-name", default=None, help="MLflow run name")
    parser.add_argument("--dataset", default=None, help="Dataset name tag")
    parser.add_argument("--dataset-version", default=None, help="Dataset version tag")
    args = parser.parse_args()

    cfg_path = Path(args.config)
    cfg = load_config(cfg_path)
    metrics = _run_benchmark(str(cfg_path), args.seconds)

    if not metrics:
        print("no samples")
        return

    print(
        f"samples={int(metrics['samples'])} "
        f"mean_ms={metrics['latency_mean_ms']:.2f} "
        f"p50={metrics['latency_p50_ms']:.2f} "
        f"p95={metrics['latency_p95_ms']:.2f} "
        f"fps={metrics['fps']:.1f}"
    )

    if not args.mlflow:
        return

    from smart_parking.experiment.mlflow_run import DatasetRef, ExperimentRun, log_model_info

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_name = args.run_name or f"benchmark-{stamp}"
    dataset = None
    if args.dataset and args.dataset_version:
        dataset = DatasetRef(args.dataset, args.dataset_version)

    with ExperimentRun(
        run_name=run_name,
        experiment_name=args.experiment,
        config_path=cfg_path,
        dataset=dataset,
        model_version=cfg.detection.model_path,
        tags={"task": "benchmark_fps"},
    ) as run:
        log_model_info(
            cfg.detection.model_path,
            cfg.detection.backend,
            {"imgsz": str(cfg.detection.imgsz)},
        )
        run.log_metrics(metrics)


if __name__ == "__main__":
    main()
