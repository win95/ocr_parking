"""Operational health summaries for GET /api/state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from smart_parking.contracts import HealthStatus, IngestState


def ms_to_iso(ts_ms: float | None) -> str | None:
    if ts_ms is None:
        return None
    return (
        datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


@dataclass
class ModelHealthSnapshot:
    last_inference_at_ms: float | None = None
    last_inference_ok: bool = True
    inference_errors: int = 0
    last_error: str | None = None


@dataclass
class OccupancyHealthSnapshot:
    last_update_at_ms: float | None = None
    last_update_ok: bool = True
    update_errors: int = 0
    last_error: str | None = None


def ingest_health(
    ing: Any,
    effective: IngestState,
    frame_age_ms: float | None,
    source_id: str,
) -> dict[str, Any]:
    status = _ingest_status(ing, effective, frame_age_ms)
    return {
        "status": status.value,
        "source_id": source_id,
        "last_frame_at": ms_to_iso(ing.last_frame_at_ms),
        "frame_age_ms": round(frame_age_ms) if frame_age_ms is not None else None,
        "reconnect_count": ing.reconnect_count,
        "last_error": ing.last_error,
        "lifecycle_state": effective.value,
    }


def model_health(
    model: ModelHealthSnapshot,
    ingest: Any,
    frame_age_ms: float | None,
) -> dict[str, Any]:
    return {
        "status": _model_status(model, ingest, frame_age_ms).value,
        "last_inference_at": ms_to_iso(model.last_inference_at_ms),
        "inference_errors": model.inference_errors,
        "last_error": model.last_error,
    }


def occupancy_health(
    occ: OccupancyHealthSnapshot,
    model: ModelHealthSnapshot,
    ingest: Any,
    frame_age_ms: float | None,
) -> dict[str, Any]:
    return {
        "status": _occupancy_status(occ, model, ingest, frame_age_ms).value,
        "last_update_at": ms_to_iso(occ.last_update_at_ms),
        "update_errors": occ.update_errors,
        "last_error": occ.last_error,
    }


def baseline_metrics(metrics: Any | None) -> dict[str, Any]:
    """FPS, latency, drops and resources from the latest processed frame."""
    if metrics is None:
        return {
            "fps": None,
            "pipeline_latency_ms": None,
            "dropped_frames": None,
            "ram_mb": None,
            "gpu_util_percent": None,
            "vram_mb": None,
            "frame_id": None,
            "updated_at": None,
        }
    stages = getattr(metrics, "stages", None) or []
    latency = sum(float(s.duration_ms) for s in stages)
    return {
        "fps": round(float(metrics.fps), 2) if metrics.fps else 0.0,
        "pipeline_latency_ms": round(latency, 2),
        "dropped_frames": int(metrics.dropped_frames),
        "ram_mb": round(metrics.ram_mb, 2) if metrics.ram_mb is not None else None,
        "gpu_util_percent": metrics.gpu_util,
        "vram_mb": round(metrics.vram_mb, 2) if metrics.vram_mb is not None else None,
        "frame_id": metrics.frame_id,
        "correlation_id": getattr(metrics, "correlation_id", None),
        "updated_at": ms_to_iso(float(metrics.timestamp_ms)),
    }


def overall_health(
    ingest_st: HealthStatus,
    model_st: HealthStatus,
    occ_st: HealthStatus,
) -> str:
    order = {HealthStatus.UNHEALTHY: 3, HealthStatus.DEGRADED: 2, HealthStatus.HEALTHY: 1}
    worst = max(ingest_st, model_st, occ_st, key=lambda s: order[s])
    return worst.value


def pipeline_sync_hint(ing: Any) -> dict[str, Any]:
    """Compare last received frame vs last pipeline completion."""
    lag_ms = None
    if ing.last_frame_at_ms is not None and ing.last_pipeline_at_ms is not None:
        lag_ms = max(0.0, ing.last_frame_at_ms - ing.last_pipeline_at_ms)
    return {
        "last_frame_at": ms_to_iso(ing.last_frame_at_ms),
        "last_pipeline_at": ms_to_iso(ing.last_pipeline_at_ms),
        "frame_to_pipeline_lag_ms": round(lag_ms) if lag_ms is not None else None,
    }


def _ingest_status(
    ing: Any,
    effective: IngestState,
    frame_age_ms: float | None,
) -> HealthStatus:
    if ing.state == IngestState.ERROR or effective == IngestState.ERROR:
        return HealthStatus.UNHEALTHY
    if effective == IngestState.STALE:
        return HealthStatus.DEGRADED
    if frame_age_ms is not None and frame_age_ms > ing.stale_threshold_ms:
        return HealthStatus.DEGRADED
    if ing.last_frame_at_ms is None:
        return HealthStatus.DEGRADED
    return HealthStatus.HEALTHY


def _model_status(
    model: ModelHealthSnapshot,
    ingest: Any,
    frame_age_ms: float | None,
) -> HealthStatus:
    if model.inference_errors > 0 and not model.last_inference_ok:
        return HealthStatus.UNHEALTHY
    if ingest.last_frame_at_ms is None:
        return HealthStatus.DEGRADED
    if model.last_inference_at_ms is None:
        return HealthStatus.DEGRADED
    if model.last_inference_at_ms < ingest.last_frame_at_ms - 1.0:
        return HealthStatus.DEGRADED
    return HealthStatus.HEALTHY


def _occupancy_status(
    occ: OccupancyHealthSnapshot,
    model: ModelHealthSnapshot,
    ingest: Any,
    frame_age_ms: float | None,
) -> HealthStatus:
    if occ.update_errors > 0 and not occ.last_update_ok:
        return HealthStatus.UNHEALTHY
    if ingest.last_frame_at_ms is None:
        return HealthStatus.DEGRADED
    if occ.last_update_at_ms is None:
        return HealthStatus.DEGRADED
    if model.last_inference_at_ms and occ.last_update_at_ms < model.last_inference_at_ms - 1.0:
        return HealthStatus.DEGRADED
    return HealthStatus.HEALTHY
