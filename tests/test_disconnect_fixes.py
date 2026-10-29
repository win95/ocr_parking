"""Fixes for client disconnect: read timeout, UI quit, operational alerts."""

from __future__ import annotations

import threading
import time

import numpy as np
import pytest

from smart_parking import app as app_module
from smart_parking.analytics.alert_engine import AlertEngine
from smart_parking.config import AlertsConfig, AppConfig
from smart_parking.ingest.read_guard import read_with_timeout
from smart_parking.pipeline.observability import INSPECTOR_STORE
from smart_parking.runtime import session as session_module
from smart_parking.runtime.frame_processor import StreamExitReason
from smart_parking.types import FrameContext


class BlockingSource:
    """Simulates hung RTSP read."""

    def __init__(self) -> None:
        self.closed = False
        self._last_read_error: str | None = None

    @property
    def is_live(self) -> bool:
        return True

    @property
    def last_read_error(self) -> str | None:
        return self._last_read_error

    def read(self):
        threading.Event().wait(30.0)
        return None

    def close(self) -> None:
        self.closed = True


def test_read_with_timeout_closes_and_sets_error() -> None:
    src = BlockingSource()
    t0 = time.perf_counter()
    assert read_with_timeout(src, 200.0) is None
    assert time.perf_counter() - t0 < 2.0
    assert src.closed is True
    assert "timeout" in (src.last_read_error or "").lower()


def test_evaluate_from_store_ingest_degraded(tmp_path) -> None:
    INSPECTOR_STORE.configure_ingest("rtsp://x", stale_frame_ms=1000.0)
    ts = 1_000_000.0
    INSPECTOR_STORE.record_frame_received(ts)
    INSPECTOR_STORE.record_pipeline_processed(ts, 5)
    INSPECTOR_STORE.set_last_alert_context(
        {"frame_id": 5, "correlation_id": "abc", "utilization_pct": 0, "slot_statuses": {}}
    )
    log_path = tmp_path / "alerts.jsonl"
    engine = AlertEngine(
        AlertsConfig(enabled=True, log_path=str(log_path), cooldown_seconds=0.0, on_ingest_degraded=True)
    )
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "smart_parking.pipeline.observability.time.time",
            lambda: (ts + 2500.0) / 1000.0,
        )
        fired = engine.evaluate_from_store("cam0")
    assert any(a["code"] == "ingest_degraded" for a in fired)


def test_user_quit_skips_reconnect(monkeypatch) -> None:
    opened: list[object] = []

    class _Src:
        is_live = True

        def close(self) -> None:
            pass

    def fake_open(_cfg, _stream=None):
        opened.append(_Src())
        return opened[-1]

    monkeypatch.setattr(session_module, "open_frame_source", fake_open)
    monkeypatch.setattr(session_module, "ModularPipeline", lambda _c: object())
    monkeypatch.setattr(session_module, "KPIEngine", lambda *_a: object())
    monkeypatch.setattr(session_module, "load_slots", lambda _p: ["s1"])
    monkeypatch.setattr(session_module, "start_inspector", lambda _c: None)
    monkeypatch.setattr(session_module, "cv2", type("C", (), {"destroyAllWindows": staticmethod(lambda: None)})())
    monkeypatch.setattr(
        session_module,
        "consume_frames",
        lambda *_a, **_k: StreamExitReason.USER_QUIT,
    )

    cfg = AppConfig(source="rtsp://192.0.2.1/parking")
    cfg = cfg.model_copy(update={"ui": cfg.ui.model_copy(update={"enabled": True})})
    INSPECTOR_STORE.configure_ingest(cfg.source, cfg.ingest.stale_frame_ms)
    app_module.run_app(cfg)
    assert len(opened) == 1
