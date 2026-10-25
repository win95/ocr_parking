"""Ingest lifecycle exposed via INSPECTOR_STORE."""

from __future__ import annotations

import time

from smart_parking.contracts import IngestState
from smart_parking.pipeline.observability import INSPECTOR_STORE


def test_ingest_lifecycle_and_stale() -> None:
    INSPECTOR_STORE.configure_ingest("rtsp://test/parking", stale_frame_ms=1000.0)
    INSPECTOR_STORE.set_reconnect_count(2)
    INSPECTOR_STORE.set_ingest_state(IngestState.CONNECTING)
    INSPECTOR_STORE.record_stream_opened()
    assert INSPECTOR_STORE.ingest_status(0).state == IngestState.STREAM_AVAILABLE

    ts = 10_000.0
    INSPECTOR_STORE.record_frame_received(ts)
    INSPECTOR_STORE.record_pipeline_processed(ts, 0)
    status = INSPECTOR_STORE.ingest_status(ts + 100.0)
    assert status.state == IngestState.PIPELINE_PROCESSING
    assert status.effective_state == IngestState.PIPELINE_PROCESSING
    assert status.reconnect_count == 2
    assert status.frames_received == 1
    assert status.frames_processed == 1

    stale = INSPECTOR_STORE.ingest_status(ts + 2000.0)
    assert stale.effective_state == IngestState.STALE
    assert stale.frame_age_ms == 2000.0


def test_ingest_error_and_api_dict() -> None:
    INSPECTOR_STORE.set_ingest_error("cannot open stream")
    payload = INSPECTOR_STORE.to_dict()
    assert payload["ingest"]["status"] == "UNHEALTHY"
    assert payload["ingest"]["last_error"] == "cannot open stream"
    assert payload["ingest_detail"]["effective_state"] == "ERROR"


def test_video_source_read_error() -> None:
    from unittest.mock import MagicMock, patch

    from smart_parking.ingest.sources import VideoSource

    with patch("smart_parking.ingest.sources.cv2.VideoCapture") as cap_cls:
        cap = MagicMock()
        cap.isOpened.return_value = True
        cap.read.return_value = (False, None)
        cap_cls.return_value = cap
        src = VideoSource("rtsp://127.0.0.1:8554/parking")
        src.open()
        assert src.read() is None
        assert src.last_read_error is not None
