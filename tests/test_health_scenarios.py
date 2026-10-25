"""Health API scenarios: RTSP loss, stale, model/occupancy errors, reconnect."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from smart_parking.contracts import (
    HealthStatus,
    PipelineMetrics,
    StageTiming,
)
from smart_parking.pipeline.health import ModelHealthSnapshot, OccupancyHealthSnapshot
from smart_parking.pipeline.observability import INSPECTOR_STORE, IngestSnapshot

_REQUIRED_STATE_KEYS = frozenset(
    {
        "metrics",
        "layers",
        "logs",
        "previews",
        "fusion_disagreements",
        "config_mode",
        "ingest",
        "model",
        "occupancy",
        "pipeline_sync",
        "baseline",
        "overall_status",
        "ingest_detail",
    }
)


@pytest.fixture(autouse=True)
def _reset_store() -> None:
    INSPECTOR_STORE.snapshot.ingest = IngestSnapshot()
    INSPECTOR_STORE.snapshot.model = ModelHealthSnapshot()
    INSPECTOR_STORE.snapshot.occupancy = OccupancyHealthSnapshot()
    INSPECTOR_STORE.configure_ingest(
        "rtsp://192.0.2.1:8554/parking",
        stale_frame_ms=1000.0,
        source_id="parking_cam_01",
    )


def test_api_state_backward_compatible_keys() -> None:
    payload = INSPECTOR_STORE.to_dict()
    assert _REQUIRED_STATE_KEYS <= payload.keys()
    assert isinstance(payload["ingest"], dict)
    assert payload["ingest"]["status"] in {s.value for s in HealthStatus}


def test_rtsp_loss_unhealthy() -> None:
    INSPECTOR_STORE.set_ingest_error("cannot open stream: rtsp://192.0.2.1:8554/parking")
    payload = INSPECTOR_STORE.to_dict()
    assert payload["ingest"]["status"] == HealthStatus.UNHEALTHY.value
    assert payload["overall_status"] == HealthStatus.UNHEALTHY.value
    assert "cannot open stream" in (payload["ingest"]["last_error"] or "")


def test_frame_stale_degraded_ingest_healthy_model() -> None:
    ts = 1_700_000_000_000.0
    INSPECTOR_STORE.record_stream_opened()
    INSPECTOR_STORE.record_frame_received(ts)
    INSPECTOR_STORE.record_pipeline_processed(ts, 10)
    INSPECTOR_STORE.record_model_inference(ts, True, None)
    INSPECTOR_STORE.record_occupancy_update(ts, True, None)

    frozen = (ts + 2500.0) / 1000.0
    with patch("smart_parking.pipeline.observability.time.time", return_value=frozen):
        payload = INSPECTOR_STORE.to_dict()

    assert payload["ingest"]["status"] == HealthStatus.DEGRADED.value
    assert payload["ingest"]["frame_age_ms"] >= 1000
    assert payload["model"]["status"] == HealthStatus.HEALTHY.value
    assert payload["occupancy"]["status"] == HealthStatus.HEALTHY.value
    assert payload["overall_status"] == HealthStatus.DEGRADED.value


def test_model_inference_error_unhealthy() -> None:
    ts = 1000.0
    INSPECTOR_STORE.record_frame_received(ts)
    INSPECTOR_STORE.record_model_inference(ts, False, "CUDA OOM")
    payload = INSPECTOR_STORE.to_dict()
    assert payload["model"]["status"] == HealthStatus.UNHEALTHY.value
    assert payload["model"]["inference_errors"] == 1
    assert payload["overall_status"] == HealthStatus.UNHEALTHY.value


def test_occupancy_update_error_unhealthy() -> None:
    ts = 1000.0
    INSPECTOR_STORE.record_frame_received(ts)
    INSPECTOR_STORE.record_model_inference(ts, True, None)
    INSPECTOR_STORE.record_occupancy_update(ts, False, "slot map failed")
    payload = INSPECTOR_STORE.to_dict()
    assert payload["occupancy"]["status"] == HealthStatus.UNHEALTHY.value
    assert payload["occupancy"]["update_errors"] == 1


def test_reconnect_count_exposed() -> None:
    INSPECTOR_STORE.set_reconnect_count(3)
    payload = INSPECTOR_STORE.to_dict()
    assert payload["ingest"]["reconnect_count"] == 3


def test_baseline_from_metrics() -> None:
    metrics = PipelineMetrics(
        correlation_id="abc",
        camera_id="cam1",
        frame_id=42,
        timestamp_ms=5000.0,
        fps=14.5,
        dropped_frames=2,
        stages=[
            StageTiming(stage="yolo", duration_ms=12.5, ok=True),
            StageTiming(stage="occupancy", duration_ms=3.2, ok=True),
        ],
        ram_mb=512.0,
        gpu_util=77.0,
        vram_mb=1024.5,
    )
    INSPECTOR_STORE.update_metrics(metrics)
    baseline = INSPECTOR_STORE.to_dict()["baseline"]
    assert baseline["fps"] == 14.5
    assert baseline["pipeline_latency_ms"] == 15.7
    assert baseline["dropped_frames"] == 2
    assert baseline["ram_mb"] == 512.0
    assert baseline["gpu_util_percent"] == 77.0
    assert baseline["vram_mb"] == 1024.5
    assert baseline["frame_id"] == 42
