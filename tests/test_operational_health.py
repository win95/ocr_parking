"""GET /api/state operational health blocks."""

from __future__ import annotations

from smart_parking.contracts import HealthStatus, IngestState
from smart_parking.pipeline.health import (
    ModelHealthSnapshot,
    ingest_health,
    model_health,
    occupancy_health,
)
from smart_parking.pipeline.observability import INSPECTOR_STORE


def test_stale_ingest_degraded_model_still_healthy() -> None:
    INSPECTOR_STORE.configure_ingest(
        "rtsp://test/parking",
        stale_frame_ms=1000.0,
        source_id="parking_cam_01",
    )
    ts = 1_000_000.0
    INSPECTOR_STORE.record_frame_received(ts)
    INSPECTOR_STORE.record_pipeline_processed(ts, 1)
    INSPECTOR_STORE.record_model_inference(ts, True, None)
    INSPECTOR_STORE.record_occupancy_update(ts, True, None)

    payload = INSPECTOR_STORE.to_dict()
    assert payload["ingest"]["status"] == HealthStatus.DEGRADED.value
    assert payload["ingest"]["source_id"] == "parking_cam_01"
    assert payload["ingest"]["frame_age_ms"] > 1000
    assert payload["model"]["status"] == HealthStatus.HEALTHY.value
    assert payload["occupancy"]["status"] == HealthStatus.HEALTHY.value


def test_ingest_error_surfaces_in_health() -> None:
    INSPECTOR_STORE.set_ingest_error("cannot open stream")
    payload = INSPECTOR_STORE.to_dict()
    assert payload["ingest"]["status"] == HealthStatus.UNHEALTHY.value
    assert payload["ingest_detail"]["effective_state"] == IngestState.ERROR.value


def test_health_helpers() -> None:
    class Ing:
        state = IngestState.PIPELINE_PROCESSING
        reconnect_count = 0
        stale_threshold_ms = 1000.0
        last_error = None
        last_frame_at_ms = 100.0

    block = ingest_health(Ing(), IngestState.STALE, 2000.0, "cam1")
    assert block["status"] == HealthStatus.DEGRADED.value


def test_model_health_tolerates_frame_interval_lag() -> None:
    class Ing:
        last_frame_at_ms = 10_000.0

    on_time = ModelHealthSnapshot(last_inference_at_ms=9_900.0)
    assert model_health(on_time, Ing(), 50.0)["status"] == HealthStatus.HEALTHY.value

    lagging = ModelHealthSnapshot(last_inference_at_ms=7_000.0)
    assert model_health(lagging, Ing(), 3000.0)["status"] == HealthStatus.DEGRADED.value
