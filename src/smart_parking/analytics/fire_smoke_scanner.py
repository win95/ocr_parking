"""Fire and smoke detection on a decimated frame stream (YOLO + DETR)."""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from smart_parking.config import AppConfig, FireSmokeConfig
from smart_parking.detection.detr_r50 import DetrR50Detector
from smart_parking.detection.tensorrt_runner import create_detector
from smart_parking.types import Detection


def _norm(name: str) -> str:
    return name.strip().lower()


def _match_labels(det: Detection, labels: set[str], min_conf: float) -> bool:
    if det.confidence < min_conf:
        return False
    return _norm(det.class_name) in labels


def filter_hits(
    dets: list[Detection],
    *,
    fire_labels: set[str],
    smoke_labels: set[str],
    min_confidence: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    fires: list[dict[str, Any]] = []
    smokes: list[dict[str, Any]] = []
    for det in dets:
        payload = {
            "class_name": det.class_name,
            "confidence": det.confidence,
            "bbox_xyxy": det.bbox_xyxy,
        }
        if _match_labels(det, fire_labels, min_confidence):
            fires.append(payload)
        if _match_labels(det, smoke_labels, min_confidence):
            smokes.append(payload)
    return fires, smokes


class FireSmokeScanner:
    """Runs parking models on slow samples; only fire/smoke classes matter."""

    def __init__(self, app_cfg: AppConfig, fs_cfg: FireSmokeConfig) -> None:
        self._fs = fs_cfg
        self._fire_labels = {_norm(x) for x in fs_cfg.fire_class_names}
        self._smoke_labels = {_norm(x) for x in fs_cfg.smoke_class_names}
        self._yolo = None
        self._detr: DetrR50Detector | None = None
        if fs_cfg.run_yolo and app_cfg.pipeline.layers.yolo and app_cfg.yolo:
            self._yolo = create_detector(app_cfg.yolo)
        if fs_cfg.run_detr and app_cfg.pipeline.layers.detr:
            if DetrR50Detector.is_available():
                self._detr = DetrR50Detector(app_cfg.detr)

    def scan(self, image: np.ndarray) -> dict[str, Any]:
        out: dict[str, Any] = {
            "yolo_latency_ms": None,
            "detr_latency_ms": None,
            "yolo_fire": [],
            "yolo_smoke": [],
            "detr_fire": [],
            "detr_smoke": [],
        }
        if self._yolo is not None:
            t0 = time.perf_counter()
            dets = self._yolo.detect(image)
            out["yolo_latency_ms"] = (time.perf_counter() - t0) * 1000.0
            fire, smoke = filter_hits(
                dets,
                fire_labels=self._fire_labels,
                smoke_labels=self._smoke_labels,
                min_confidence=self._fs.min_confidence,
            )
            out["yolo_fire"] = fire
            out["yolo_smoke"] = smoke
        if self._detr is not None:
            t0 = time.perf_counter()
            dets = self._detr.detect(image)
            out["detr_latency_ms"] = (time.perf_counter() - t0) * 1000.0
            fire, smoke = filter_hits(
                dets,
                fire_labels=self._fire_labels,
                smoke_labels=self._smoke_labels,
                min_confidence=self._fs.min_confidence,
            )
            out["detr_fire"] = fire
            out["detr_smoke"] = smoke
        return out

    def hits_for_alerts(self, scan: dict[str, Any]) -> list[dict[str, Any]]:
        hits: list[dict[str, Any]] = []
        for model, fire_key, smoke_key in (
            ("yolo", "yolo_fire", "yolo_smoke"),
            ("detr", "detr_fire", "detr_smoke"),
        ):
            for item in scan.get(fire_key) or []:
                hits.append({"kind": "fire", "model": model, **item})
            for item in scan.get(smoke_key) or []:
                hits.append({"kind": "smoke", "model": model, **item})
        return hits
