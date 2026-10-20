"""Structured logging, correlation IDs, and shared inspector state."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from smart_parking.contracts import PipelineMetrics, StageTiming

_log = logging.getLogger("smart_parking.pipeline")


def new_correlation_id() -> str:
    return uuid.uuid4().hex[:16]


def log_stage(
    correlation_id: str,
    camera_id: str,
    frame_id: int,
    stage: str,
    severity: str,
    message: str,
    **extra: Any,
) -> None:
    payload = {
        "correlation_id": correlation_id,
        "camera_id": camera_id,
        "frame_id": frame_id,
        "stage": stage,
        "severity": severity,
        "message": message,
        "ts_ms": time.time() * 1000,
        **extra,
    }
    line = json.dumps(payload, default=str)
    if severity == "ERROR":
        _log.error(line)
    elif severity == "WARNING":
        _log.warning(line)
    else:
        _log.info(line)
    INSPECTOR_STORE.append_log(payload)


@dataclass
class LayerHealth:
    enabled: bool = True
    available: bool = True
    healthy: bool = True
    last_ok_ms: float = 0.0
    last_error: str | None = None
    stale: bool = False


@dataclass
class InspectorSnapshot:
    """Latest state exposed to Pipeline Inspector API."""

    metrics: PipelineMetrics | None = None
    layers: dict[str, LayerHealth] = field(default_factory=dict)
    logs: list[dict[str, Any]] = field(default_factory=list)
    previews: dict[str, Any] = field(default_factory=dict)
    fusion_disagreements: int = 0
    config_mode: str = "normal"


class InspectorStateStore:
    """Thread-safe holder for inspector UI."""

    def __init__(self, max_logs: int = 500) -> None:
        self._lock = threading.Lock()
        self._max_logs = max_logs
        self.snapshot = InspectorSnapshot()

    def update_metrics(self, metrics: PipelineMetrics) -> None:
        with self._lock:
            self.snapshot.metrics = metrics

    def set_layer(self, name: str, health: LayerHealth) -> None:
        with self._lock:
            self.snapshot.layers[name] = health

    def append_log(self, entry: dict[str, Any]) -> None:
        with self._lock:
            self.snapshot.logs.append(entry)
            if len(self.snapshot.logs) > self._max_logs:
                self.snapshot.logs = self.snapshot.logs[-self._max_logs :]

    def set_preview(self, key: str, value: Any) -> None:
        with self._lock:
            self.snapshot.previews[key] = value

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            m = self.snapshot.metrics
            return {
                "metrics": m.model_dump() if m else None,
                "layers": {k: v.__dict__ for k, v in self.snapshot.layers.items()},
                "logs": list(self.snapshot.logs[-100:]),
                "previews": self.snapshot.previews,
                "fusion_disagreements": self.snapshot.fusion_disagreements,
                "config_mode": self.snapshot.config_mode,
            }


INSPECTOR_STORE = InspectorStateStore()
