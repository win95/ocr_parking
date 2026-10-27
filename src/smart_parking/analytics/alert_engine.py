"""Experimental alerts — JSONL log only (no external notify)."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from smart_parking.config import AlertsConfig
from smart_parking.contracts import OccupancyStatus
from smart_parking.pipeline.observability import INSPECTOR_STORE

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
        system: dict[str, Any] | None = None,
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

        sys_snap = system or {}
        gpu = sys_snap.get("gpu") or {}
        temp = gpu.get("temperature_c")
        if (
            self._cfg.gpu_temp_c_threshold is not None
            and temp is not None
            and temp >= self._cfg.gpu_temp_c_threshold
        ):
            self._maybe(
                fired,
                "gpu_temp_high",
                True,
                {"temperature_c": temp, "threshold": self._cfg.gpu_temp_c_threshold},
            )
        vram_pct = gpu.get("vram_percent")
        if (
            self._cfg.vram_pct_threshold is not None
            and vram_pct is not None
            and vram_pct >= self._cfg.vram_pct_threshold
        ):
            self._maybe(
                fired,
                "vram_high",
                True,
                {
                    "vram_percent": vram_pct,
                    "vram_used_mb": gpu.get("vram_used_mb"),
                    "vram_total_mb": gpu.get("vram_total_mb"),
                    "threshold": self._cfg.vram_pct_threshold,
                },
            )
        ram = sys_snap.get("ram") or {}
        ram_pct = ram.get("percent")
        if (
            self._cfg.ram_pct_threshold is not None
            and ram_pct is not None
            and ram_pct >= self._cfg.ram_pct_threshold
        ):
            self._maybe(
                fired,
                "ram_high",
                True,
                {
                    "ram_percent": ram_pct,
                    "ram_used_mb": ram.get("used_mb"),
                    "ram_total_mb": ram.get("total_mb"),
                    "threshold": self._cfg.ram_pct_threshold,
                },
            )

        for alert in fired:
            self._write(camera_id, frame_id, correlation_id, alert)
        return fired

    def notify(
        self,
        code: str,
        severity: str,
        detail: dict[str, Any],
        camera_id: str = "",
        frame_id: int = 0,
        correlation_id: str = "",
    ) -> dict[str, Any]:
        """Emit a one-off alert (e.g. pipeline_started) to log and web UI."""
        alert = {"code": code, "severity": severity, "detail": detail}
        self._write(camera_id, frame_id, correlation_id, alert)
        return alert

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
        INSPECTOR_STORE.append_alert(payload)
        _log.warning("ALERT %s frame=%s %s", alert["code"], frame_id, alert.get("detail"))
