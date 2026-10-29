"""Latest-frame buffer for slow auxiliary pipelines (fire/smoke)."""

from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FrameSample:
    frame_id: int
    timestamp_ms: float
    image: np.ndarray


class FrameSampleBuffer:
    """Thread-safe holder of the most recent main-ingest frame."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: FrameSample | None = None

    def offer(self, frame_id: int, timestamp_ms: float, image: np.ndarray) -> None:
        with self._lock:
            self._latest = FrameSample(frame_id, timestamp_ms, image.copy())

    def peek(self) -> FrameSample | None:
        with self._lock:
            if self._latest is None:
                return None
            s = self._latest
            return FrameSample(s.frame_id, s.timestamp_ms, s.image.copy())
