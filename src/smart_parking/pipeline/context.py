"""Extended pipeline frame context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from smart_parking.contracts import (
    DetectionBatch,
    PipelineMetrics,
    SlotStateContract,
    TrackContract,
)
from smart_parking.types import Detection, Track


@dataclass
class PipelineFrame:
    """Canonical per-frame pipeline carrier."""

    camera_id: str
    frame_id: int
    timestamp_ms: float
    correlation_id: str
    image: np.ndarray
    image_height: int = 0
    image_width: int = 0
    detr_batch: DetectionBatch | None = None
    yolo_batch: DetectionBatch | None = None
    fused_batch: DetectionBatch | None = None
    detections: list[Detection] = field(default_factory=list)
    tracks: list[Track] = field(default_factory=list)
    track_contracts: list[TrackContract] = field(default_factory=list)
    slot_states: dict[str, SlotStateContract] = field(default_factory=dict)
    raw_occupied: dict[str, bool] = field(default_factory=dict)
    fps: float = 0.0
    metrics: PipelineMetrics | None = None
    overlay_image: np.ndarray | None = None
    minimap_image: np.ndarray | None = None
    fusion_disagreements: int = 0
    dropped: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def ensure_dims(self) -> None:
        if self.image is not None and self.image.size:
            self.image_height, self.image_width = self.image.shape[:2]
