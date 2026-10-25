"""Ingest lifecycle signals for Inspector (server-side)."""

from __future__ import annotations

import time

from smart_parking.contracts import IngestState, IngestStatusContract
from smart_parking.pipeline.observability import INSPECTOR_STORE


def configure_ingest(
    source: str,
    stale_frame_ms: float,
    source_id: str = "",
) -> None:
    """Bind source URL and stale threshold for frame-age computation."""
    INSPECTOR_STORE.configure_ingest(source, stale_frame_ms, source_id)


def mark_connecting() -> None:
    INSPECTOR_STORE.set_ingest_state(IngestState.CONNECTING)


def mark_stream_available() -> None:
    INSPECTOR_STORE.record_stream_opened()


def mark_frame_received(timestamp_ms: float) -> None:
    INSPECTOR_STORE.record_frame_received(timestamp_ms)


def mark_pipeline_processed(timestamp_ms: float, frame_id: int) -> None:
    INSPECTOR_STORE.record_pipeline_processed(timestamp_ms, frame_id)


def mark_ingest_error(message: str) -> None:
    INSPECTOR_STORE.set_ingest_error(message)


def set_reconnect_count(count: int) -> None:
    INSPECTOR_STORE.set_reconnect_count(count)


def read_error_from_source(source: object) -> str | None:
    """Return last capture read error if the source exposes it."""
    err = getattr(source, "last_read_error", None)
    return err if isinstance(err, str) else None


def build_ingest_status(now_ms: float | None = None) -> IngestStatusContract:
    """Serialize current ingest snapshot (applies STALE when frame age exceeds threshold)."""
    return INSPECTOR_STORE.ingest_status(now_ms=now_ms or time.time() * 1000.0)
