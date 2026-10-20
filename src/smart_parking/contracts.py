"""Stable pipeline data contracts (schema v1)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

SCHEMA_VERSION = "1.0"


class CoordinateSpace(str, Enum):
    IMAGE_PIXEL = "image_pixel"


class OccupancyStatus(str, Enum):
    FREE = "FREE"
    OCCUPIED = "OCCUPIED"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"


class BBox(BaseModel):
    """Axis-aligned box in image pixel space (xyxy)."""

    x1: float
    y1: float
    x2: float
    y2: float
    space: CoordinateSpace = CoordinateSpace.IMAGE_PIXEL

    @field_validator("x2")
    @classmethod
    def x2_gt_x1(cls, v: float, info: Any) -> float:
        x1 = info.data.get("x1", 0)
        if v < x1:
            raise ValueError("x2 must be >= x1")
        return v

    @field_validator("y2")
    @classmethod
    def y2_gt_y1(cls, v: float, info: Any) -> float:
        y1 = info.data.get("y1", 0)
        if v < y1:
            raise ValueError("y2 must be >= y1")
        return v

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.x1, self.y1, self.x2, self.y2)


class DetectionContract(BaseModel):
    schema_version: str = SCHEMA_VERSION
    camera_id: str
    frame_id: int
    timestamp_ms: float
    source: Literal["detr", "yolo", "fused"]
    class_id: int
    class_name: str
    confidence: float
    bbox: BBox


class DetectionBatch(BaseModel):
    schema_version: str = SCHEMA_VERSION
    camera_id: str
    frame_id: int
    timestamp_ms: float
    source: Literal["detr", "yolo", "fused"]
    detections: list[DetectionContract] = Field(default_factory=list)


class TrackContract(BaseModel):
    track_id: int
    bbox: BBox
    confidence: float
    age: int = 0
    missed_frames: int = 0
    coasting: bool = False


class SlotStateContract(BaseModel):
    slot_id: str
    status: OccupancyStatus
    confidence: float = 0.0
    reason: str = ""
    updated_at_ms: float = 0.0
    coasting: bool = False


class ParkingEvent(BaseModel):
    schema_version: str = SCHEMA_VERSION
    correlation_id: str
    camera_id: str
    frame_id: int
    timestamp_ms: float
    event_type: str
    slot_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class StageTiming(BaseModel):
    stage: str
    duration_ms: float
    ok: bool
    error: str | None = None
    input_count: int = 0
    output_count: int = 0


class PipelineMetrics(BaseModel):
    schema_version: str = SCHEMA_VERSION
    correlation_id: str
    camera_id: str
    frame_id: int
    timestamp_ms: float
    fps: float = 0.0
    queue_depth: int = 0
    dropped_frames: int = 0
    stages: list[StageTiming] = Field(default_factory=list)
    cpu_percent: float | None = None
    ram_mb: float | None = None
    gpu_util: float | None = None
    vram_mb: float | None = None
