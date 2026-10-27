"""Application configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class DetectionConfig(BaseModel):
    """Legacy YOLO settings (alias for yolo)."""

    backend: str = "pytorch"
    model_path: str = "yolo11n.pt"
    confidence: float = 0.35
    imgsz: int = 640
    device: str = "0"
    # Keep every model output or only vehicle_classes. Turn this off to see
    # every COCO class on the overlay (useful while aiming a demo camera).
    vehicle_only: bool = True
    vehicle_classes: list[str] = Field(
        default_factory=lambda: ["car", "truck", "bus", "motorcycle", "vehicle"]
    )


class YoloConfig(DetectionConfig):
    """YOLO11 stage configuration."""


class DetrConfig(BaseModel):
    model_id: str = "facebook/detr-resnet-50-dc5"
    confidence: float = 0.5
    device: str = "cpu"
    vehicle_only: bool = True
    # Shortest edge fed to the DETR image processor. 800 is the paper default
    # (accurate, slow); 480 cuts latency ~4x on dc5 and keeps realtime on
    # mid-range GPUs. The longest edge is derived as size * 1.66.
    size: int = 800


class FusionConfig(BaseModel):
    strategy: Literal["yolo_only", "detr_only", "union", "weighted_nms"] = "yolo_only"
    iou_threshold: float = 0.5
    detr_weight: float = 0.45
    yolo_weight: float = 0.55


class LayerFlags(BaseModel):
    ingest: bool = True
    detr: bool = False
    yolo: bool = True
    fusion: bool = False
    tracking: bool = True
    occupancy: bool = True
    overlay: bool = True
    minimap: bool = False


class PipelineConfig(BaseModel):
    mode: Literal["normal", "debug", "replay", "benchmark"] = "normal"
    camera_id: str = "cam0"
    queue_max: int = 1
    drop_frames_in_realtime: bool = True
    stop_on_stage_error: bool = True
    # Cap processed frames per second (None = process every incoming frame).
    max_fps: float | None = None

    @field_validator("max_fps")
    @classmethod
    def positive_fps(cls, value: float | None) -> float | None:
        if value is not None and value <= 0:
            raise ValueError("max_fps must be > 0")
        return value

    @model_validator(mode="after")
    def replay_no_drop(self) -> PipelineConfig:
        if self.mode == "replay":
            object.__setattr__(self, "drop_frames_in_realtime", False)
        return self

    layers: LayerFlags = Field(default_factory=LayerFlags)


class OccupancyConfig(BaseModel):
    vehicle_classes: list[str] = Field(
        default_factory=lambda: ["car", "truck", "bus", "motorcycle", "vehicle"]
    )
    unknown_on_empty: bool = False
    stale_after_ms: float = 60_000.0


class IngestConfig(BaseModel):
    """Video ingest settings (RTSP transport, reconnect policy)."""

    rtsp_transport: Literal["tcp", "udp"] = "tcp"
    connect_timeout_ms: int = 8000
    reconnect: bool = True
    reconnect_delay_seconds: float = 3.0
    max_reconnects: int | None = None
    stale_frame_ms: float = 5000.0


class InspectorConfig(BaseModel):
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8765


class ArtifactsConfig(BaseModel):
    enabled: bool = False
    directory: str = "logs/artifacts"
    max_frames: int = 100
    sample_every_n: int = 30


class SmoothingConfig(BaseModel):
    window: int = 15
    t_on: int = 10
    t_off: int = 12


class TrackingConfig(BaseModel):
    coast_frames: int = 8
    iou_threshold: float = 0.3


class UiConfig(BaseModel):
    enabled: bool = True
    panel_width: int = 280


class AlertsConfig(BaseModel):
    """Experimental alerts — JSONL log only (phase 1)."""

    enabled: bool = False
    log_path: str = "logs/alerts.jsonl"
    cooldown_seconds: float = 30.0
    on_ingest_degraded: bool = True
    on_ingest_unhealthy: bool = True
    on_model_unhealthy: bool = True
    on_slot_stale: bool = True
    utilization_pct_threshold: float | None = None
    # Server resources (None = rule disabled).
    gpu_temp_c_threshold: float | None = None
    vram_pct_threshold: float | None = None
    ram_pct_threshold: float | None = None
    save_frame_dir: str | None = None


class AnalyticsConfig(BaseModel):
    log_path: str = "logs/events.jsonl"
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)


class AppConfig(BaseModel):
    source: str = "data/sample.mp4"
    slots_path: str = "configs/slots/parking_lot_01.json"
    ingest: IngestConfig = Field(default_factory=IngestConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    yolo: YoloConfig | None = None
    detr: DetrConfig = Field(default_factory=DetrConfig)
    fusion: FusionConfig = Field(default_factory=FusionConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    occupancy: OccupancyConfig = Field(default_factory=OccupancyConfig)
    smoothing: SmoothingConfig = Field(default_factory=SmoothingConfig)
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    ui: UiConfig = Field(default_factory=UiConfig)
    analytics: AnalyticsConfig = Field(default_factory=AnalyticsConfig)
    inspector: InspectorConfig = Field(default_factory=InspectorConfig)
    artifacts: ArtifactsConfig = Field(default_factory=ArtifactsConfig)
    replay_path: str | None = None

    @model_validator(mode="after")
    def sync_yolo_and_layers(self) -> AppConfig:
        if self.yolo is None:
            self.yolo = YoloConfig(**self.detection.model_dump())
        if self.pipeline.layers.fusion and not (
            self.pipeline.layers.detr and self.pipeline.layers.yolo
        ):
            raise ValueError("fusion requires both detr and yolo enabled")
        return self

    @field_validator("source")
    @classmethod
    def validate_source_path(cls, value: str) -> str:
        if value.startswith(("webcam:", "rtsp://")):
            return value
        if ".." in Path(value).parts:
            raise ValueError("source path must not contain '..'")
        return value


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load YAML config from path or SMART_PARKING_CONFIG env."""
    cfg_path = path or os.environ.get("SMART_PARKING_CONFIG", "configs/default.yaml")
    with open(cfg_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return AppConfig.model_validate(data)
