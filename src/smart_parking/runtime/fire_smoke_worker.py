"""Background worker: slow fire/smoke scans on frames decoupled from main FPS."""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING

from smart_parking.analytics.fire_smoke_scanner import FireSmokeScanner
from smart_parking.config import AppConfig
from smart_parking.pipeline.frame_sample_buffer import FrameSampleBuffer
from smart_parking.pipeline.observability import get_inspector_store, new_correlation_id
from smart_parking.runtime.local_display import save_alert_frame_from_raw

if TYPE_CHECKING:
    from smart_parking.analytics.alert_engine import AlertEngine

_log = logging.getLogger("smart_parking.fire_smoke")


class FireSmokeWorker:
    def __init__(
        self,
        cfg: AppConfig,
        buffer: FrameSampleBuffer,
        alerts: AlertEngine | None,
    ) -> None:
        self._cfg = cfg
        self._buffer = buffer
        self._alerts = alerts
        self._fs = cfg.fire_smoke
        self._scanner = FireSmokeScanner(cfg, self._fs)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_frame_id = -1

    def start(self) -> None:
        if not self._fs.enabled:
            return
        self._thread = threading.Thread(target=self._loop, name="fire-smoke", daemon=True)
        self._thread.start()
        _log.info(
            "Fire/smoke stream started (interval=%.1fs)",
            self._fs.scan_interval_seconds,
        )

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)

    def _loop(self) -> None:
        cam = self._cfg.pipeline.camera_id
        store = get_inspector_store(cam)
        interval = max(0.5, float(self._fs.scan_interval_seconds))
        while not self._stop.is_set():
            if self._stop.wait(interval):
                break
            sample = self._buffer.peek()
            if sample is None:
                continue
            correlation_id = new_correlation_id()
            scan = self._scanner.scan(sample.image)
            hits = self._scanner.hits_for_alerts(scan)
            now_ms = time.time() * 1000.0
            payload = {
                "stream": "fire_smoke",
                "scan_interval_seconds": interval,
                "last_scan_ms": now_ms,
                "frame_id": sample.frame_id,
                "timestamp_ms": sample.timestamp_ms,
                "correlation_id": correlation_id,
                "yolo_latency_ms": scan.get("yolo_latency_ms"),
                "detr_latency_ms": scan.get("detr_latency_ms"),
                "hit_count": len(hits),
                "hits": hits[:20],
            }
            store.set_fire_smoke(payload)
            store.set_fire_smoke_frame(
                {
                    "frame_id": sample.frame_id,
                    "correlation_id": correlation_id,
                    "timestamp_ms": sample.timestamp_ms,
                    "stream": "fire_smoke",
                    "hit_count": len(hits),
                }
            )
            fired: list[dict] = []
            if self._alerts is not None:
                fired = self._alerts.evaluate_fire_smoke(
                    camera_id=cam,
                    frame_id=sample.frame_id,
                    correlation_id=correlation_id,
                    hits=hits,
                )
            save_dir = self._fs.save_frame_dir or self._cfg.analytics.alerts.save_frame_dir
            if fired and save_dir:
                save_alert_frame_from_raw(
                    save_dir,
                    cam,
                    sample.frame_id,
                    correlation_id,
                    sample.image,
                    fired[0]["code"],
                )
            self._last_frame_id = sample.frame_id
