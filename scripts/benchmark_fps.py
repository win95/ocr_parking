#!/usr/bin/env python3
"""Benchmark inference latency."""

from __future__ import annotations

import argparse
import statistics
import time

from smart_parking.config import load_config
from smart_parking.detection.tensorrt_runner import create_detector
from smart_parking.ingest import FrameLoop, parse_source


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--seconds", type=float, default=30.0)
    args = parser.parse_args()

    cfg = load_config(args.config)
    detector = create_detector(cfg.detection)
    source = parse_source(cfg.source)
    source.open()
    loop = FrameLoop(source, max_queue=1)

    latencies: list[float] = []
    end = time.perf_counter() + args.seconds
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
        print("no samples")
        return
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    mean = statistics.mean(latencies)
    fps = 1000.0 / mean if mean > 0 else 0
    print(f"samples={len(latencies)} mean_ms={mean:.2f} p50={p50:.2f} p95={p95:.2f} fps={fps:.1f}")


if __name__ == "__main__":
    main()
