"""Detector protocol."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from smart_parking.types import Detection


class DetectorProtocol(Protocol):
    """Object detector interface."""

    def detect(self, image: np.ndarray) -> list[Detection]:
        """Run inference on a BGR image."""
        ...
