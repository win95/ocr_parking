"""Pipeline stage base."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

from smart_parking.contracts import StageTiming
from smart_parking.pipeline.context import PipelineFrame
from smart_parking.pipeline.observability import LayerHealth, log_stage


class PipelineStage(ABC):
    """Timed, observable stage."""

    name: str

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def run(self, frame: PipelineFrame) -> StageTiming:
        if not self.enabled:
            return StageTiming(stage=self.name, duration_ms=0, ok=True, output_count=0)
        t0 = time.perf_counter()
        err: str | None = None
        ok = True
        inp, out = 0, 0
        try:
            inp, out = self._execute(frame)
        except Exception as exc:
            ok = False
            err = str(exc)
            log_stage(
                frame.correlation_id,
                frame.camera_id,
                frame.frame_id,
                self.name,
                "ERROR",
                err,
            )
        ms = (time.perf_counter() - t0) * 1000.0
        return StageTiming(
            stage=self.name,
            duration_ms=ms,
            ok=ok,
            error=err,
            input_count=inp,
            output_count=out,
        )

    @abstractmethod
    def _execute(self, frame: PipelineFrame) -> tuple[int, int]:
        """Return input_count, output_count."""

    def health(self, timing: StageTiming) -> LayerHealth:
        return LayerHealth(
            enabled=self.enabled,
            available=True,
            healthy=timing.ok,
            last_ok_ms=time.time() * 1000 if timing.ok else 0,
            last_error=timing.error,
        )
