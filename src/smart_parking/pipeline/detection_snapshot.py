"""Compact detection summary for Inspector (no image data)."""

from __future__ import annotations

from typing import Any

from smart_parking.pipeline.context import PipelineFrame


def summarize_detections(frame: PipelineFrame, max_samples: int = 20) -> dict[str, Any]:
    """Build JSON-safe detection stats for the current frame."""
    by_class: dict[str, int] = {}
    for det in frame.detections:
        name = det.class_name or str(det.class_id)
        by_class[name] = by_class.get(name, 0) + 1

    yolo_count = (
        len(frame.yolo_batch.detections) if frame.yolo_batch is not None else 0
    )
    detr_count = (
        len(frame.detr_batch.detections) if frame.detr_batch is not None else 0
    )
    samples = [
        {
            "class_name": d.class_name,
            "confidence": round(float(d.confidence), 4),
            "bbox_xyxy": [round(float(x), 1) for x in d.bbox_xyxy],
        }
        for d in frame.detections[:max_samples]
    ]
    yolo_ms = _stage_ms(frame, "yolo")
    detr_ms = _stage_ms(frame, "detr")
    return {
        "frame_id": frame.frame_id,
        "correlation_id": frame.correlation_id,
        "fused_count": len(frame.detections),
        "yolo_count": yolo_count,
        "detr_count": detr_count,
        "track_count": len(frame.tracks),
        "by_class": by_class,
        "yolo_latency_ms": yolo_ms,
        "detr_latency_ms": detr_ms,
        "samples": samples,
        "truncated": len(frame.detections) > max_samples,
    }


def _stage_ms(frame: PipelineFrame, name: str) -> float | None:
    if frame.metrics is None:
        return None
    for st in frame.metrics.stages:
        if st.stage == name:
            return round(float(st.duration_ms), 2)
    return None
