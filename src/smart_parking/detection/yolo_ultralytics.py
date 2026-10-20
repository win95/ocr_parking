"""Ultralytics YOLO11 detector."""

from __future__ import annotations

import numpy as np

from smart_parking.config import DetectionConfig
from smart_parking.types import Detection


class YoloDetector:
    """YOLO backend using Ultralytics."""

    def __init__(self, cfg: DetectionConfig) -> None:
        from ultralytics import YOLO

        self._cfg = cfg
        self._model = YOLO(cfg.model_path)

    def detect(self, image: np.ndarray) -> list[Detection]:
        results = self._model.predict(
            image,
            imgsz=self._cfg.imgsz,
            conf=self._cfg.confidence,
            device=self._cfg.device,
            verbose=False,
        )
        out: list[Detection] = []
        if not results:
            return out
        r0 = results[0]
        if r0.boxes is None:
            return out
        names = r0.names or {}
        for box in r0.boxes:
            xyxy = box.xyxy[0].tolist()
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            name = str(names.get(cls_id, cls_id))
            out.append(
                Detection(
                    bbox_xyxy=(xyxy[0], xyxy[1], xyxy[2], xyxy[3]),
                    confidence=conf,
                    class_id=cls_id,
                    class_name=name,
                )
            )
        return out
