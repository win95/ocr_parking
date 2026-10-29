"""Detection summary for Inspector API."""

from smart_parking.pipeline.context import PipelineFrame
from smart_parking.pipeline.detection_snapshot import summarize_detections
from smart_parking.types import Detection


def test_summarize_detections_counts_by_class() -> None:
    frame = PipelineFrame(
        camera_id="c1",
        frame_id=3,
        timestamp_ms=1000.0,
        correlation_id="abc",
        image=__import__("numpy").zeros((480, 640, 3), dtype=__import__("numpy").uint8),
    )
    frame.detections = [
        Detection(class_id=2, class_name="car", confidence=0.9, bbox_xyxy=(10, 10, 50, 50)),
        Detection(class_id=2, class_name="car", confidence=0.8, bbox_xyxy=(60, 60, 90, 90)),
    ]
    summary = summarize_detections(frame, max_samples=5)
    assert summary["fused_count"] == 2
    assert summary["by_class"]["car"] == 2
    assert len(summary["samples"]) == 2
