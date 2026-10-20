"""Video and webcam sources."""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from pathlib import Path

import cv2
import numpy as np

from smart_parking.types import FrameContext

_WEBCAM_RE = re.compile(r"^webcam:(\d+)$")


class FrameSource(ABC):
    """Abstract frame source."""

    @abstractmethod
    def open(self) -> None:
        ...

    @abstractmethod
    def read(self) -> FrameContext | None:
        ...

    @abstractmethod
    def close(self) -> None:
        ...

    def __enter__(self) -> FrameSource:
        self.open()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


class VideoSource(FrameSource):
    """Read frames from a video file."""

    def __init__(self, path: str) -> None:
        if ".." in Path(path).parts:
            raise ValueError("invalid video path")
        self._path = path
        self._cap: cv2.VideoCapture | None = None
        self._frame_id = 0

    def open(self) -> None:
        cap = cv2.VideoCapture(self._path)
        if not cap.isOpened():
            raise FileNotFoundError(f"cannot open video: {self._path}")
        self._cap = cap

    def read(self) -> FrameContext | None:
        if self._cap is None:
            return None
        ok, frame = self._cap.read()
        if not ok:
            return None
        ctx = FrameContext(
            frame_id=self._frame_id,
            timestamp_ms=time.time() * 1000.0,
            image=frame,
        )
        self._frame_id += 1
        return ctx

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class WebcamSource(FrameSource):
    """Read frames from a webcam device index."""

    def __init__(self, index: int = 0) -> None:
        self._index = index
        self._cap: cv2.VideoCapture | None = None
        self._frame_id = 0

    def open(self) -> None:
        cap = cv2.VideoCapture(self._index)
        if not cap.isOpened():
            raise RuntimeError(f"cannot open webcam:{self._index}")
        self._cap = cap

    def read(self) -> FrameContext | None:
        if self._cap is None:
            return None
        ok, frame = self._cap.read()
        if not ok:
            return None
        ctx = FrameContext(
            frame_id=self._frame_id,
            timestamp_ms=time.time() * 1000.0,
            image=frame,
        )
        self._frame_id += 1
        return ctx

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None


def parse_source(spec: str) -> FrameSource:
    """Parse source string into a FrameSource."""
    spec = spec.strip()
    match = _WEBCAM_RE.match(spec)
    if match:
        return WebcamSource(int(match.group(1)))
    if spec.startswith("rtsp://"):
        return VideoSource(spec)
    return VideoSource(spec)
