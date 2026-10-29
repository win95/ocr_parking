"""Timed reads for live streams (avoid blocking forever on client disconnect)."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from smart_parking.ingest.sources import FrameSource
    from smart_parking.types import FrameContext

_UNSET = object()


def read_with_timeout(
    source: FrameSource,
    timeout_ms: float,
) -> FrameContext | None:
    """Read one frame; on timeout close source and set last_read_error if possible."""
    if timeout_ms <= 0:
        return source.read()

    result: list[object] = [_UNSET]

    def _worker() -> None:
        result[0] = source.read()

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()
    worker.join(timeout=timeout_ms / 1000.0)
    if worker.is_alive():
        source.close()
        message = "read timeout (stream stall or client disconnect)"
        if hasattr(source, "_last_read_error"):
            source._last_read_error = message
        return None

    if result[0] is _UNSET:
        return None
    return result[0]  # type: ignore[return-value]
