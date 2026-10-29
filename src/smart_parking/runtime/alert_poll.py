"""Background alert evaluation when frames are not processed (stall / reconnect gap)."""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from smart_parking.analytics.alert_engine import AlertEngine


class AlertPollWorker:
    """Periodically evaluate alerts from Inspector health snapshot."""

    def __init__(
        self,
        engine: AlertEngine,
        camera_id: str,
        interval_seconds: float = 5.0,
    ) -> None:
        self._engine = engine
        self._camera_id = camera_id
        self._interval = max(1.0, interval_seconds)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=self._interval + 1.0)

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            self._engine.evaluate_from_store(self._camera_id)
