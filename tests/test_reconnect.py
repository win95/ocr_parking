"""Reconnect loop for live sources (RTSP/webcam)."""

from __future__ import annotations

import time

import numpy as np

from smart_parking import app as app_module
from smart_parking.config import AppConfig
from smart_parking.pipeline.observability import INSPECTOR_STORE
from smart_parking.types import FrameContext


class FakeSource:
    """Yields a fixed number of frames, then reports end-of-stream."""

    def __init__(self, frames: int = 2) -> None:
        self._frames = frames
        self.opened = False
        self.closed = False

    @property
    def is_live(self) -> bool:
        return True

    def open(self) -> None:
        self.opened = True

    def read(self):
        if self._frames <= 0:
            return None
        self._frames -= 1
        return FrameContext(
            frame_id=0,
            timestamp_ms=time.time() * 1000.0,
            image=np.zeros((480, 640, 3), dtype=np.uint8),
        )

    def close(self) -> None:
        self.closed = True

    @property
    def last_read_error(self) -> str | None:
        if self._frames <= 0:
            return "end of test stream"
        return None


class StubPipeline:
    def __init__(self, _cfg: AppConfig) -> None:
        self.processed = 0

    def process(self, pf):
        self.processed += 1
        return pf

    def mark_dropped(self) -> None:
        pass


class StubKPI:
    def __init__(self, _total: int, _log_path: str) -> None:
        pass

    def update(self, _states):
        return {}


def _config(**ingest) -> AppConfig:
    cfg = AppConfig(source="rtsp://192.0.2.1:8554/parking")
    cfg = cfg.model_copy(update={"ui": cfg.ui.model_copy(update={"enabled": False})})
    cfg = cfg.model_copy(update={"ingest": cfg.ingest.model_copy(update=ingest)})
    return cfg


def _patch(monkeypatch, sources: list[FakeSource]) -> list[FakeSource]:
    opened: list[FakeSource] = []

    def fake_open(_cfg):
        src = sources[len(opened)] if len(opened) < len(sources) else sources[-1]
        src.open()
        opened.append(src)
        return src

    monkeypatch.setattr(app_module, "_open_source", fake_open)
    monkeypatch.setattr(app_module, "ModularPipeline", StubPipeline)
    monkeypatch.setattr(app_module, "KPIEngine", StubKPI)
    monkeypatch.setattr(app_module, "load_slots", lambda _p: ["slot-1"])
    return opened


def test_reconnects_until_limit(monkeypatch) -> None:
    sources = [FakeSource(frames=2) for _ in range(5)]
    opened = _patch(monkeypatch, sources)
    cfg = _config(reconnect=True, reconnect_delay_seconds=0.01, max_reconnects=2)

    INSPECTOR_STORE.configure_ingest(cfg.source, cfg.ingest.stale_frame_ms)
    app_module.run_app(cfg)

    assert len(opened) == 3  # initial + 2 reconnects
    assert all(src.closed for src in opened)
    assert INSPECTOR_STORE.snapshot.ingest.reconnect_count == 2
    assert INSPECTOR_STORE.snapshot.ingest.frames_processed >= 2


def test_stops_when_reconnect_disabled(monkeypatch) -> None:
    sources = [FakeSource(frames=2) for _ in range(5)]
    opened = _patch(monkeypatch, sources)
    cfg = _config(reconnect=False)

    INSPECTOR_STORE.configure_ingest(cfg.source, cfg.ingest.stale_frame_ms)
    app_module.run_app(cfg)

    assert len(opened) == 1


def test_file_source_does_not_reconnect(monkeypatch) -> None:
    """A finite source (file) must not be re-opened in a loop."""

    class FileSource(FakeSource):
        @property
        def is_live(self) -> bool:
            return False

    sources = [FileSource(frames=2) for _ in range(5)]
    opened = _patch(monkeypatch, sources)
    cfg = _config(reconnect=True, reconnect_delay_seconds=0.01)

    INSPECTOR_STORE.configure_ingest(cfg.source, cfg.ingest.stale_frame_ms)
    app_module.run_app(cfg)

    assert len(opened) == 1


def test_survives_open_failure(monkeypatch) -> None:
    """A source that fails to open is retried until the limit is reached."""
    sources = [FakeSource(frames=1) for _ in range(3)]

    def fake_open(_cfg):
        raise RuntimeError("cannot open stream")

    monkeypatch.setattr(app_module, "_open_source", fake_open)
    monkeypatch.setattr(app_module, "ModularPipeline", StubPipeline)
    monkeypatch.setattr(app_module, "KPIEngine", StubKPI)
    monkeypatch.setattr(app_module, "load_slots", lambda _p: ["slot-1"])
    cfg = _config(reconnect=True, reconnect_delay_seconds=0.01, max_reconnects=1)

    INSPECTOR_STORE.configure_ingest(cfg.source, cfg.ingest.stale_frame_ms)
    app_module.run_app(cfg)
