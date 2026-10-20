"""Phase 2 DETR detector stub."""

from __future__ import annotations

import numpy as np

from smart_parking.types import Detection


class DetrDetectorStub:
    """Placeholder for detr-r50-dc5 integration."""

    def detect(self, image: np.ndarray) -> list[Detection]:
        raise NotImplementedError("DETR backend is phase 2; use YoloDetector for MVP")
