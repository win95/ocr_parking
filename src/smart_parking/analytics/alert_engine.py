"""Experimental alerts — JSONL log only (no external notify)."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from smart_parking.config import AlertsConfig
from smart_parking.contracts import OccupancyStatus

_log = logging.getLogger("smart_parking.alerts")


class AlertEngine:
    """Evaluate rules and append structured warnings to a log file."""

    def __init__(self, cfg: AlertsConfig) -> None:
        self._cfg = cfg
        self._path = Path(cfg.log_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._last_fired: dict[str, float] = {}

    def evaluate(
        self,
        *,
        camera_id: str,
        frame_id: int,
        correlation_id: str,
        utilization_pct: float,
        slot_statuses: dict[str, str],
        health: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if not self._cfg.enabled:
            return []
        fired: list[dict[str, Any]] = []
        ing = health.get("ingest") or {}
        mod = health.get("model") or {}
        self._maybe(
            fired,
            "ingest_unhealthy",
            self._cfg.on_ingest_unhealthy and ing.get("status") == "UNHEALTHY",
            ing,
        )
        self._maybe(
            fired,
            "ingest_degraded",
            self._cfg.on_ingest_degraded and ing.get("status") == "DEGRADED",
            ing,
        )
        self._maybe(
            fired,
            "model_unhealthy",
            self._cfg.on_model_unhealthy and mod.get("status") == "UNHEALTHY",
            mod,
        )
        if self._cfg.utilization_pct_threshold is not None:
            over = utilization_pct >= self._cfg.utilization_pct_threshold
            self._maybe(
                fired,
                "utilization_high",
                over,
                {"utilization_pct": utilization_pct, "threshold": self._cfg.utilization_pct_threshold},
            )
        if self._cfg.on_slot_stale:
            stale_slots = [sid for sid, st in slot_statuses.items() if st == OccupancyStatus.STALE.value]
            if stale_slots:
                self._maybe(fired, "slot_stale", True, {"slot_ids": stale_slots})

        for alert in fired:
            self._write(camera_id, frame_id, correlation_id, alert)
        return fired

    def _maybe(
        self,
        out: list[dict[str, Any]],
        code: str,
        condition: bool,
        detail: dict[str, Any],
    ) -> None:
        if not condition or not self._cooldown_ok(code):
            return
        out.append({"code": code, "severity": "warning", "detail": detail})
        self._last_fired[code] = time.time()

    def _cooldown_ok(self, code: str) -> bool:
        last = self._last_fired.get(code, 0.0)
        return (time.time() - last) >= self._cfg.cooldown_seconds

    def _write(
        self,
        camera_id: str,
        frame_id: int,
        correlation_id: str,
        alert: dict[str, Any],
    ) -> None:
        payload = {
            "ts": time.time(),
            "camera_id": camera_id,
            "frame_id": frame_id,
            "correlation_id": correlation_id,
            "channel": "log",
            **alert,
        }
        line = json.dumps(payload, default=str)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        _log.warning("ALERT %s frame=%s %s", alert["code"], frame_id, alert.get("detail"))
        from smart_parking.pipeline.observability import get_inspector_store

        get_inspector_store(camera_id).append_alert(
            {
                "ts_ms": payload["ts"] * 1000,
                "camera_id": camera_id,
                "frame_id": frame_id,
                "correlation_id": correlation_id,
                "code": alert["code"],
                "severity": alert.get("severity", "warning"),
                "detail": alert.get("detail"),
            }
        )
