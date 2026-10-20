"""Frame artifact persistence for replay/debug."""

from __future__ import annotations

import json
from pathlib import Path

from smart_parking.contracts import DetectionBatch, SCHEMA_VERSION
from smart_parking.pipeline.context import PipelineFrame


class ArtifactStore:
    """Save/load intermediate outputs with retention limits."""

    def __init__(self, directory: str, max_frames: int = 100) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._max = max_frames
        self._index: list[str] = sorted(
            p.stem for p in self._dir.glob("*.json")
        )[-max_frames:]

    def maybe_save(self, frame: PipelineFrame, every_n: int) -> None:
        if frame.frame_id % every_n != 0:
            return
        key = f"{frame.camera_id}_{frame.frame_id:06d}"
        self._index.append(key)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "correlation_id": frame.correlation_id,
            "camera_id": frame.camera_id,
            "frame_id": frame.frame_id,
            "timestamp_ms": frame.timestamp_ms,
            "detr": frame.detr_batch.model_dump() if frame.detr_batch else None,
            "yolo": frame.yolo_batch.model_dump() if frame.yolo_batch else None,
            "fused": frame.fused_batch.model_dump() if frame.fused_batch else None,
            "fusion_disagreements": frame.fusion_disagreements,
            "metrics": frame.metrics.model_dump() if frame.metrics else None,
        }
        path = self._dir / f"{key}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        while len(self._index) > self._max:
            old = self._index.pop(0)
            (self._dir / f"{old}.json").unlink(missing_ok=True)

    def load(self, key: str) -> dict:
        return json.loads((self._dir / f"{key}.json").read_text(encoding="utf-8"))

    def list_keys(self) -> list[str]:
        return sorted(self._index)
