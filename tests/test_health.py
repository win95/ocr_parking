from types import SimpleNamespace

from smart_parking.pipeline.health import (
    ModelHealthSnapshot,
    OccupancyHealthSnapshot,
    _model_status,
    _occupancy_status,
    overall_health,
)
from smart_parking.contracts import HealthStatus


def _ingest(last_frame_ms: float, stale_ms: float = 5000.0) -> SimpleNamespace:
    return SimpleNamespace(
        last_frame_at_ms=last_frame_ms,
        stale_threshold_ms=stale_ms,
        reconnect_count=0,
        last_error=None,
    )


def test_model_healthy_while_frame_arrives_during_inference() -> None:
    """A live stream delivers the next frame while the pipeline is still busy."""
    ing = _ingest(last_frame_ms=10_100.0)
    model = ModelHealthSnapshot(last_inference_at_ms=10_000.0)
    assert _model_status(model, ing, 20.0) is HealthStatus.HEALTHY


def test_model_degraded_when_inference_stalls() -> None:
    ing = _ingest(last_frame_ms=20_000.0, stale_ms=5000.0)
    model = ModelHealthSnapshot(last_inference_at_ms=10_000.0)
    assert _model_status(model, ing, 20.0) is HealthStatus.DEGRADED


def test_model_degraded_when_never_ran() -> None:
    ing = _ingest(last_frame_ms=10_000.0)
    assert _model_status(ModelHealthSnapshot(), ing, 20.0) is HealthStatus.DEGRADED


def test_occupancy_healthy_when_one_frame_behind() -> None:
    ing = _ingest(last_frame_ms=10_050.0)
    model = ModelHealthSnapshot(last_inference_at_ms=10_000.0)
    occ = OccupancyHealthSnapshot(last_update_at_ms=9_950.0)
    assert _occupancy_status(occ, model, ing, 20.0) is HealthStatus.HEALTHY


def test_occupancy_degraded_when_stalled() -> None:
    ing = _ingest(last_frame_ms=10_050.0, stale_ms=5000.0)
    model = ModelHealthSnapshot(last_inference_at_ms=10_000.0)
    occ = OccupancyHealthSnapshot(last_update_at_ms=1_000.0)
    assert _occupancy_status(occ, model, ing, 20.0) is HealthStatus.DEGRADED


def test_overall_health_takes_worst() -> None:
    assert (
        overall_health(HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.HEALTHY)
        == "DEGRADED"
    )
    assert (
        overall_health(HealthStatus.HEALTHY, HealthStatus.HEALTHY, HealthStatus.UNHEALTHY)
        == "UNHEALTHY"
    )
    assert (
        overall_health(HealthStatus.HEALTHY, HealthStatus.HEALTHY, HealthStatus.HEALTHY)
        == "HEALTHY"
    )
