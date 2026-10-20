"""Detection normalization and validation."""

from __future__ import annotations

from smart_parking.contracts import BBox, DetectionBatch, DetectionContract
from smart_parking.types import Detection


def validate_bbox(
    bbox: tuple[float, float, float, float],
    width: int,
    height: int,
) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = bbox
    x1 = max(0.0, min(float(width), x1))
    x2 = max(0.0, min(float(width), x2))
    y1 = max(0.0, min(float(height), y1))
    y2 = max(0.0, min(float(height), y2))
    if x2 < x1 or y2 < y1:
        raise ValueError("invalid bbox after clamp")
    return (x1, y1, x2, y2)


def to_contract(
    det: Detection,
    camera_id: str,
    frame_id: int,
    timestamp_ms: float,
    source: str,
    width: int,
    height: int,
) -> DetectionContract:
    xyxy = validate_bbox(det.bbox_xyxy, width, height)
    return DetectionContract(
        camera_id=camera_id,
        frame_id=frame_id,
        timestamp_ms=timestamp_ms,
        source=source,
        class_id=det.class_id,
        class_name=det.class_name,
        confidence=det.confidence,
        bbox=BBox(x1=xyxy[0], y1=xyxy[1], x2=xyxy[2], y2=xyxy[3]),
    )


def batch_from_detections(
    dets: list[Detection],
    camera_id: str,
    frame_id: int,
    timestamp_ms: float,
    source: str,
    width: int,
    height: int,
) -> DetectionBatch:
    items = [
        to_contract(d, camera_id, frame_id, timestamp_ms, source, width, height)
        for d in dets
    ]
    return DetectionBatch(
        camera_id=camera_id,
        frame_id=frame_id,
        timestamp_ms=timestamp_ms,
        source=source,
        detections=items,
    )


def detections_from_batch(batch: DetectionBatch) -> list[Detection]:
    out: list[Detection] = []
    for d in batch.detections:
        t = d.bbox.as_tuple()
        out.append(
            Detection(
                bbox_xyxy=t,
                confidence=d.confidence,
                class_id=d.class_id,
                class_name=d.class_name,
            )
        )
    return out
