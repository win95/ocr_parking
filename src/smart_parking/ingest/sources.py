"""Video and webcam sources."""

from __future__ import annotations

import os
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path

import cv2
import numpy as np

from smart_parking.types import FrameContext

_WEBCAM_RE = re.compile(r"^webcam:(\d+)$")
_RTSP_PREFIX = "rtsp://"
_CAPTURE_OPTIONS_ENV = "OPENCV_FFMPEG_CAPTURE_OPTIONS"


def _parse_capture_options(raw: str) -> dict[str, str]:
    """Parse OPENCV_FFMPEG_CAPTURE_OPTIONS into a key/value mapping.

    OpenCV hands this string to ``av_dict_parse_string(options, ";", "|", 0)``:
    pairs are separated by ``|`` and each pair is ``key;value``.
    """
    options: dict[str, str] = {}
    for pair in raw.split("|"):
        pair = pair.strip()
        if not pair:
            continue
        key, _, value = pair.partition(";")
        options[key.strip()] = value.strip()
    return options


def _apply_capture_options(transport: str, timeout_ms: int) -> None:
    """Pin FFmpeg capture options for RTSP (transport + connect timeout).

    OpenCV reads OPENCV_FFMPEG_CAPTURE_OPTIONS when the FFmpeg backend opens
    the capture, so this must be set before VideoCapture() is constructed.

    The value must use FFmpeg's av_dict syntax (``key;value`` pairs joined by
    ``|``) — a plain ``;``-separated list makes FFmpeg read everything after
    the first separator as a single value and the capture fails to open.
    """
    options = _parse_capture_options(os.environ.get(_CAPTURE_OPTIONS_ENV, ""))
    options["rtsp_transport"] = transport
    options["timeout"] = str(int(timeout_ms) * 1000)
    os.environ[_CAPTURE_OPTIONS_ENV] = "|".join(f"{k};{v}" for k, v in options.items())


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

    @property
    def is_live(self) -> bool:
        """True for continuous sources (RTSP/webcam) that can be re-opened."""
        return False

    @property
    def last_read_error(self) -> str | None:
        """Last capture read failure, if any."""
        return None

    def __enter__(self) -> FrameSource:
        self.open()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


class VideoSource(FrameSource):
    """Read frames from a video file or an RTSP stream."""

    def __init__(
        self,
        path: str,
        rtsp_transport: str = "tcp",
        connect_timeout_ms: int = 8000,
    ) -> None:
        if ".." in Path(path).parts:
            raise ValueError("invalid video path")
        self._path = path
        self._rtsp_transport = rtsp_transport
        self._connect_timeout_ms = connect_timeout_ms
        self._cap: cv2.VideoCapture | None = None
        self._frame_id = 0
        self._last_read_error: str | None = None

    @property
    def is_live(self) -> bool:
        return self._path.startswith(_RTSP_PREFIX)

    @property
    def last_read_error(self) -> str | None:
        return self._last_read_error

    def open(self) -> None:
        if self.is_live:
            _apply_capture_options(self._rtsp_transport, self._connect_timeout_ms)
            cap = cv2.VideoCapture(self._path, cv2.CAP_FFMPEG)
        else:
            cap = cv2.VideoCapture(self._path)
        if not cap.isOpened():
            cap.release()
            if self.is_live:
                raise RuntimeError(f"cannot open stream: {self._path}")
            raise FileNotFoundError(f"cannot open video: {self._path}")
        self._cap = cap

    def read(self) -> FrameContext | None:
        if self._cap is None:
            return None
        ok, frame = self._cap.read()
        if not ok:
            self._last_read_error = "VideoCapture.read() failed (end of stream or RTSP error)"
            return None
        self._last_read_error = None
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
        self._last_read_error: str | None = None

    @property
    def is_live(self) -> bool:
        return True

    @property
    def last_read_error(self) -> str | None:
        return self._last_read_error

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
            self._last_read_error = "VideoCapture.read() failed (webcam disconnected?)"
            return None
        self._last_read_error = None
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


def is_live_source(spec: str) -> bool:
    """True when the spec points to a continuous source (RTSP/webcam)."""
    spec = spec.strip()
    return spec.startswith(_RTSP_PREFIX) or bool(_WEBCAM_RE.match(spec))


def parse_source(
    spec: str,
    rtsp_transport: str = "tcp",
    connect_timeout_ms: int = 8000,
) -> FrameSource:
    """Parse source string into a FrameSource."""
    spec = spec.strip()
    match = _WEBCAM_RE.match(spec)
    if match:
        return WebcamSource(int(match.group(1)))
    if spec.startswith(_RTSP_PREFIX):
        return VideoSource(
            spec,
            rtsp_transport=rtsp_transport,
            connect_timeout_ms=connect_timeout_ms,
        )
    return VideoSource(spec)
