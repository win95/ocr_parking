"""Structured logging, correlation IDs, and shared inspector state."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from smart_parking.contracts import (
    HealthStatus,
    IngestState,
    IngestStatusContract,
    PipelineMetrics,
    StageTiming,
)
from smart_parking.pipeline.health import (
    ModelHealthSnapshot,
    OccupancyHealthSnapshot,
    baseline_metrics,
    ingest_health,
    model_health,
    occupancy_health,
    overall_health,
    pipeline_sync_hint,
)

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
    INSPECTOR_REGISTRY.get_store(camera_id).append_log(payload)


@dataclass
class LayerHealth:
    enabled: bool = True
    available: bool = True
    healthy: bool = True
    last_ok_ms: float = 0.0
    last_error: str | None = None
    stale: bool = False


@dataclass
class IngestSnapshot:
    """Server-side ingest lifecycle (not client PUBLISHING)."""

    state: IngestState = IngestState.IDLE
    source: str = ""
    source_id: str = ""
    stale_threshold_ms: float = 5000.0
    reconnect_count: int = 0
    frames_received: int = 0
    frames_processed: int = 0
    last_frame_at_ms: float | None = None
    last_pipeline_at_ms: float | None = None
    last_pipeline_frame_id: int | None = None
    stream_opened_at_ms: float | None = None
    last_error: str | None = None


@dataclass
class InspectorSnapshot:
    """Latest state exposed to Pipeline Inspector API."""

    metrics: PipelineMetrics | None = None
    layers: dict[str, LayerHealth] = field(default_factory=dict)
    logs: list[dict[str, Any]] = field(default_factory=list)
    previews: dict[str, Any] = field(default_factory=dict)
    fusion_disagreements: int = 0
    config_mode: str = "normal"
    model_registry_id: str | None = None
    ingest: IngestSnapshot = field(default_factory=IngestSnapshot)
    model: ModelHealthSnapshot = field(default_factory=ModelHealthSnapshot)
    occupancy: OccupancyHealthSnapshot = field(default_factory=OccupancyHealthSnapshot)
    recent_alerts: list[dict[str, Any]] = field(default_factory=list)
    current_frame: dict[str, Any] = field(default_factory=dict)
    last_alert_context: dict[str, Any] = field(default_factory=dict)


class InspectorStateStore:
    """Thread-safe holder for inspector UI."""

    def __init__(self, max_logs: int = 500, max_alerts: int = 50) -> None:
        self._lock = threading.Lock()
        self._max_logs = max_logs
        self._max_alerts = max_alerts
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

    def append_alert(self, entry: dict[str, Any]) -> None:
        with self._lock:
            self.snapshot.recent_alerts.append(entry)
            if len(self.snapshot.recent_alerts) > self._max_alerts:
                self.snapshot.recent_alerts = self.snapshot.recent_alerts[
                    -self._max_alerts :
                ]

    def set_current_frame(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.snapshot.current_frame = payload

    def set_model_registry_id(self, registry_id: str | None) -> None:
        with self._lock:
            self.snapshot.model_registry_id = registry_id

    def set_last_alert_context(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.snapshot.last_alert_context = payload

    def set_preview(self, key: str, value: Any) -> None:
        with self._lock:
            self.snapshot.previews[key] = value

    def configure_ingest(
        self,
        source: str,
        stale_frame_ms: float,
        source_id: str = "",
    ) -> None:
        with self._lock:
            ing = self.snapshot.ingest
            ing.source = source
            ing.source_id = source_id or source
            ing.stale_threshold_ms = stale_frame_ms

    def record_model_inference(
        self,
        timestamp_ms: float,
        ok: bool,
        error: str | None = None,
    ) -> None:
        with self._lock:
            m = self.snapshot.model
            if ok:
                m.last_inference_at_ms = timestamp_ms
                m.last_inference_ok = True
            else:
                m.inference_errors += 1
                m.last_inference_ok = False
                m.last_error = error

    def record_occupancy_update(
        self,
        timestamp_ms: float,
        ok: bool,
        error: str | None = None,
    ) -> None:
        with self._lock:
            o = self.snapshot.occupancy
            if ok:
                o.last_update_at_ms = timestamp_ms
                o.last_update_ok = True
            else:
                o.update_errors += 1
                o.last_update_ok = False
                o.last_error = error

    def set_ingest_state(self, state: IngestState) -> None:
        with self._lock:
            self.snapshot.ingest.state = state

    def set_reconnect_count(self, count: int) -> None:
        with self._lock:
            self.snapshot.ingest.reconnect_count = count

    def set_ingest_error(self, message: str) -> None:
        with self._lock:
            ing = self.snapshot.ingest
            ing.state = IngestState.ERROR
            ing.last_error = message

    def record_stream_opened(self) -> None:
        with self._lock:
            ing = self.snapshot.ingest
            ing.stream_opened_at_ms = time.time() * 1000.0
            ing.state = IngestState.STREAM_AVAILABLE
            ing.last_error = None

    def record_frame_received(self, timestamp_ms: float) -> None:
        with self._lock:
            ing = self.snapshot.ingest
            ing.frames_received += 1
            ing.last_frame_at_ms = timestamp_ms
            ing.state = IngestState.FRAME_RECEIVED

    def record_pipeline_processed(self, timestamp_ms: float, frame_id: int) -> None:
        with self._lock:
            ing = self.snapshot.ingest
            ing.frames_processed += 1
            ing.last_pipeline_at_ms = timestamp_ms
            ing.last_pipeline_frame_id = frame_id
            ing.state = IngestState.PIPELINE_PROCESSING

    def ingest_status(self, now_ms: float) -> IngestStatusContract:
        with self._lock:
            ing = self.snapshot.ingest
            return _ingest_contract(ing, now_ms)

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            m = self.snapshot.metrics
            now_ms = time.time() * 1000.0
            ing_snap = self.snapshot.ingest
            detail = _ingest_contract(ing_snap, now_ms)
            effective = detail.effective_state
            frame_age = detail.frame_age_ms
            sid = ing_snap.source_id or ing_snap.source
            ing_h = ingest_health(ing_snap, effective, frame_age, sid)
            mod_h = model_health(self.snapshot.model, ing_snap, frame_age)
            occ_h = occupancy_health(
                self.snapshot.occupancy,
                self.snapshot.model,
                ing_snap,
                frame_age,
            )
            ing_st = HealthStatus(ing_h["status"])
            mod_st = HealthStatus(mod_h["status"])
            occ_st = HealthStatus(occ_h["status"])
            return {
                "metrics": m.model_dump() if m else None,
                "layers": {k: v.__dict__ for k, v in self.snapshot.layers.items()},
                "logs": list(self.snapshot.logs[-100:]),
                "previews": self.snapshot.previews,
                "fusion_disagreements": self.snapshot.fusion_disagreements,
                "config_mode": self.snapshot.config_mode,
                "model_registry_id": self.snapshot.model_registry_id,
                "ingest": ing_h,
                "model": mod_h,
                "occupancy": occ_h,
                "pipeline_sync": pipeline_sync_hint(ing_snap),
                "baseline": baseline_metrics(m),
                "overall_status": overall_health(ing_st, mod_st, occ_st),
                "ingest_detail": detail.model_dump(),
                "recent_alerts": list(self.snapshot.recent_alerts[-50:]),
                "current_frame": dict(self.snapshot.current_frame),
            }


def _effective_ingest_state(ing: IngestSnapshot, now_ms: float) -> IngestState:
    if ing.state == IngestState.ERROR:
        return IngestState.ERROR
    if ing.last_frame_at_ms is None:
        return ing.state
    age = now_ms - ing.last_frame_at_ms
    if (
        ing.state == IngestState.PIPELINE_PROCESSING
        and age > ing.stale_threshold_ms
    ):
        return IngestState.STALE
    return ing.state


def _ingest_contract(ing: IngestSnapshot, now_ms: float) -> IngestStatusContract:
    frame_age = None
    if ing.last_frame_at_ms is not None:
        frame_age = max(0.0, now_ms - ing.last_frame_at_ms)
    effective = _effective_ingest_state(ing, now_ms)
    return IngestStatusContract(
        state=ing.state,
        effective_state=effective,
        source=ing.source,
        publishing_observable=False,
        last_frame_at_ms=ing.last_frame_at_ms,
        frame_age_ms=frame_age,
        last_pipeline_at_ms=ing.last_pipeline_at_ms,
        reconnect_count=ing.reconnect_count,
        frames_received=ing.frames_received,
        frames_processed=ing.frames_processed,
        last_error=ing.last_error,
        stream_opened_at_ms=ing.stream_opened_at_ms,
        stale_threshold_ms=ing.stale_threshold_ms,
    )


class InspectorRegistry:
    """Per-camera inspector stores plus configured stream metadata."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stores: dict[str, InspectorStateStore] = {}
        self._active_id = "cam0"
        self._configured: list[dict[str, Any]] = []

    def configure_streams(
        self,
        streams: list[Any],
        active_id: str,
        model_registry_id: str | None = None,
    ) -> None:
        with self._lock:
            self._active_id = active_id
            self._configured = [
                {
                    "id": s.id,
                    "source": s.source,
                    "enabled": s.enabled,
                    "slots_path": s.slots_path,
                }
                for s in streams
            ]
            for stream in streams:
                store = self._stores.setdefault(stream.id, InspectorStateStore())
                store.set_model_registry_id(model_registry_id)

    def set_active(self, camera_id: str) -> None:
        with self._lock:
            self._active_id = camera_id

    def get_store(self, camera_id: str | None = None) -> InspectorStateStore:
        cid = camera_id or self._active_id
        with self._lock:
            return self._stores.setdefault(cid, InspectorStateStore())

    @property
    def active_store(self) -> InspectorStateStore:
        return self.get_store(None)

    def list_cameras(self) -> list[dict[str, Any]]:
        with self._lock:
            out: list[dict[str, Any]] = []
            for meta in self._configured:
                cid = meta["id"]
                store = self._stores.get(cid)
                summary = store.to_dict() if store else {}
                out.append(
                    {
                        **meta,
                        "active": cid == self._active_id,
                        "overall_status": summary.get("overall_status", "IDLE"),
                    }
                )
            if not out and self._stores:
                for cid, store in self._stores.items():
                    out.append(
                        {
                            "id": cid,
                            "source": store.snapshot.ingest.source,
                            "enabled": True,
                            "active": cid == self._active_id,
                            "overall_status": store.to_dict().get("overall_status"),
                        }
                    )
            return out

    def to_dict(self, camera_id: str | None = None) -> dict[str, Any]:
        cid = camera_id or self._active_id
        payload = self.get_store(cid).to_dict()
        payload["active_camera_id"] = self._active_id
        payload["cameras"] = self.list_cameras()
        return payload


class _ActiveInspectorProxy:
    """Backward-compatible delegate to the active camera store."""

    def __getattr__(self, name: str) -> Any:
        return getattr(INSPECTOR_REGISTRY.active_store, name)

    def to_dict(self) -> dict[str, Any]:
        return INSPECTOR_REGISTRY.to_dict()


INSPECTOR_REGISTRY = InspectorRegistry()
INSPECTOR_STORE = _ActiveInspectorProxy()


def get_inspector_store(camera_id: str) -> InspectorStateStore:
    return INSPECTOR_REGISTRY.get_store(camera_id)
