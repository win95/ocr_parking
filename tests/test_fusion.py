from __future__ import annotations

from smart_parking.config import FusionConfig
from smart_parking.contracts import BBox, DetectionBatch, DetectionContract
from smart_parking.detection.fusion import count_disagreements, fuse_frame
from smart_parking.pipeline.context import PipelineFrame
from smart_parking.types import Detection


def _batch(source: str, bbox: tuple[float, float, float, float]) -> DetectionBatch:
    return DetectionBatch(
        camera_id="c",
        frame_id=1,
        timestamp_ms=1.0,
        source=source,
        detections=[
            DetectionContract(
                camera_id="c",
                frame_id=1,
                timestamp_ms=1.0,
                source=source,
                class_id=0,
                class_name="car",
                confidence=0.9,
                bbox=BBox(x1=bbox[0], y1=bbox[1], x2=bbox[2], y2=bbox[3]),
            )
        ],
    )


def test_fusion_union() -> None:
    frame = PipelineFrame("c", 1, 1.0, "corr", image=__import__("numpy").zeros((100, 100, 3), dtype="uint8"))
    frame.image_width, frame.image_height = 100, 100
    frame.detr_batch = _batch("detr", (10, 10, 40, 40))
    frame.yolo_batch = _batch("yolo", (12, 12, 42, 42))
    cfg = FusionConfig(strategy="union", iou_threshold=0.3)
    out = fuse_frame(frame, cfg)
    assert len(out) == 1


def test_disagreement_count() -> None:
    a = [Detection((10, 10, 20, 20), 0.9, 0, "car")]
    b = [Detection((80, 80, 90, 90), 0.9, 0, "car")]
    assert count_disagreements(a, b, 0.3) == 2
