"""TensorRT detector wrapper (optional dependency)."""

from __future__ import annotations

import numpy as np

from smart_parking.detection.yolo_ultralytics import YoloDetector
from smart_parking.config import DetectionConfig, YoloConfig
from smart_parking.types import Detection


class TensorRTDetector:
    """Use TensorRT export via Ultralytics when engine path is provided."""

    def __init__(self, cfg: DetectionConfig) -> None:
        self._cfg = cfg
        path = cfg.model_path
        if not path.endswith(".engine"):
            raise ValueError("tensorrt backend requires .engine model_path")
        try:
            from ultralytics import YOLO

            self._model = YOLO(path)
            self._fallback: YoloDetector | None = None
        except Exception:
            self._model = None
            self._fallback = YoloDetector(cfg)

    def detect(self, image: np.ndarray) -> list[Detection]:
        if self._fallback is not None:
            return self._fallback.detect(image)
        results = self._model.predict(
            image,
            imgsz=self._cfg.imgsz,
            conf=self._cfg.confidence,
            device=self._cfg.device,
            verbose=False,
        )
        det = YoloDetector(self._cfg)
        det._model = self._model
        return det.detect(image)


def create_detector(cfg: DetectionConfig | YoloConfig):
    """Factory for pytorch vs tensorrt backends."""
    if cfg.backend == "tensorrt":
        return TensorRTDetector(cfg)
    return YoloDetector(cfg)
