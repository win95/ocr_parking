"""Integration test with mocked detectors."""

from __future__ import annotations

import numpy as np

from smart_parking.config import AppConfig
from smart_parking.pipeline.context import PipelineFrame
from smart_parking.pipeline.runner import ModularPipeline
from smart_parking.types import Detection


class _FakeYolo:
    def detect(self, image: np.ndarray) -> list[Detection]:
        h, w = image.shape[:2]
        return [Detection((w * 0.2, h * 0.2, w * 0.4, h * 0.4), 0.9, 0, "car")]


def test_pipeline_yolo_only(monkeypatch) -> None:
    cfg = AppConfig()
    monkeypatch.setattr(
        "smart_parking.pipeline.runner.create_detector",
        lambda _c: _FakeYolo(),
    )
    pipe = ModularPipeline(cfg)
    frame = PipelineFrame("cam0", 0, 0.0, "abc", image=np.zeros((480, 640, 3), dtype=np.uint8))
    out = pipe.process(frame)
    assert out.yolo_batch is not None
    assert out.metrics is not None
    assert out.metrics.stages
