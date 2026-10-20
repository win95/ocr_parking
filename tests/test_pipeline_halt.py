import numpy as np

from smart_parking.config import AppConfig, PipelineConfig
from smart_parking.pipeline.context import PipelineFrame
from smart_parking.pipeline.runner import ModularPipeline


def test_halt_on_yolo_failure(monkeypatch) -> None:
    cfg = AppConfig(pipeline=PipelineConfig(stop_on_stage_error=True))

    class _BadYolo:
        def detect(self, _img):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "smart_parking.pipeline.runner.create_detector",
        lambda _c: _BadYolo(),
    )
    pipe = ModularPipeline(cfg)
    frame = PipelineFrame("c", 0, 0.0, "id", image=np.zeros((100, 100, 3), dtype=np.uint8))
    out = pipe.process(frame)
    assert out.extra.get("pipeline_halted") is True
    assert out.detections == []
