"""Shared pipeline types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Detection:
    """Single object detection."""

    bbox_xyxy: tuple[float, float, float, float]
    confidence: float
    class_id: int
    class_name: str


@dataclass
class Track:
    """Multi-object track."""

    track_id: int
    bbox_xyxy: tuple[float, float, float, float]
    confidence: float
    coasting: bool = False


@dataclass
class SlotState:
    """Per-slot occupancy after smoothing."""

    slot_id: str
    occupied: bool
    coasting: bool = False


@dataclass
class FrameContext:
    """Carrier through the pipeline."""

    frame_id: int
    timestamp_ms: float
    image: np.ndarray
    detections: list[Detection] = field(default_factory=list)
    raw_occupied: dict[str, bool] = field(default_factory=dict)
    slot_states: dict[str, SlotState] = field(default_factory=dict)
    tracks: list[Track] = field(default_factory=list)
    fps: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)
