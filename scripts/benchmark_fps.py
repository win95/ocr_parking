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
from smart_parking.ingest.frame_loop import FrameLoop
from smart_parking.ingest.registry import effective_app_config, open_frame_source, resolve_active_stream
from smart_parking.pipeline.context import PipelineFrame
from smart_parking.pipeline.gpu_stats import read_gpu_utilization
from smart_parking.pipeline.observability import new_correlation_id
from smart_parking.pipeline.runner import ModularPipeline


def _run_detector_benchmark(cfg_path: str, seconds: float) -> dict[str, float]:
    cfg = load_config(cfg_path)
    run_cfg = effective_app_config(cfg)
    active = resolve_active_stream(cfg)
    detector = create_detector(run_cfg.detection)
    source = open_frame_source(run_cfg, active)
    loop = FrameLoop(source, max_queue=run_cfg.pipeline.queue_max)

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

    return _summarize_latencies(latencies)


def _run_pipeline_benchmark(cfg_path: str, seconds: float) -> dict[str, float]:
    cfg = load_config(cfg_path)
    run_cfg = effective_app_config(cfg)
    active = resolve_active_stream(cfg)
    pipeline = ModularPipeline(run_cfg)
    source = open_frame_source(run_cfg, active)
    loop = FrameLoop(source, max_queue=run_cfg.pipeline.queue_max)

    latencies: list[float] = []
    end = time.perf_counter() + seconds
    warmup = 50
    idx = 0
    gpu_util_sum = 0.0
    gpu_samples = 0

    try:
        for ctx in loop:
            if time.perf_counter() > end:
                break
            t0 = time.perf_counter()
            pf = PipelineFrame(
                camera_id=run_cfg.pipeline.camera_id,
                frame_id=ctx.frame_id,
                timestamp_ms=ctx.timestamp_ms,
                correlation_id=new_correlation_id(),
                image=ctx.image,
            )
            pf.extra["queue_depth"] = loop.queue_depth
            pipeline.process(pf)
            dt = (time.perf_counter() - t0) * 1000.0
            idx += 1
            if idx > warmup:
                latencies.append(dt)
                util, _ = read_gpu_utilization()
                if util is not None:
                    gpu_util_sum += util
                    gpu_samples += 1
    finally:
        source.close()

    out = _summarize_latencies(latencies)
    if gpu_samples:
        out["gpu_util_mean"] = gpu_util_sum / gpu_samples
    return out


def _summarize_latencies(latencies: list[float]) -> dict[str, float]:
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
        "pipeline_latency_ms": mean,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--pipeline", action="store_true", help="Benchmark full ModularPipeline")
    parser.add_argument("--mlflow", action="store_true", help="Log run to MLflow")
    parser.add_argument("--experiment", default=None, help="MLflow experiment name")
    parser.add_argument("--run-name", default=None, help="MLflow run name")
    parser.add_argument("--dataset", default=None, help="Dataset name tag")
    parser.add_argument("--dataset-version", default=None, help="Dataset version tag")
    args = parser.parse_args()

    cfg_path = Path(args.config)
    cfg = load_config(cfg_path)
    if args.pipeline:
        metrics = _run_pipeline_benchmark(str(cfg_path), args.seconds)
    else:
        metrics = _run_detector_benchmark(str(cfg_path), args.seconds)

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
    exp_name = args.experiment or cfg.mlflow.experiment_name

    with ExperimentRun(
        run_name=run_name,
        experiment_name=exp_name,
        config_path=cfg_path,
        dataset=dataset,
        model_version=cfg.detection.model_path,
        tags={"task": "benchmark_pipeline" if args.pipeline else "benchmark_fps"},
    ) as run:
        log_model_info(
            cfg.detection.model_path,
            cfg.detection.backend,
            {
                "imgsz": str(cfg.detection.imgsz),
                "models_active": str(cfg.models.active or ""),
            },
        )
        run.log_metrics(metrics)


if __name__ == "__main__":
    main()
