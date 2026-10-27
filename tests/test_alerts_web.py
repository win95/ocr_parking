from smart_parking.analytics.alert_engine import AlertEngine
from smart_parking.config import AlertsConfig
from smart_parking.pipeline.observability import INSPECTOR_STORE, InspectorStateStore


def test_notify_reaches_inspector_store(tmp_path) -> None:
    engine = AlertEngine(
        AlertsConfig(
            enabled=True,
            log_path=str(tmp_path / "alerts.jsonl"),
            cooldown_seconds=0.0,
        )
    )
    engine.notify(
        "pipeline_started",
        "info",
        {"source": "rtsp://example/stream"},
        camera_id="cam1",
    )
    last = INSPECTOR_STORE.alerts(limit=1)[0]
    assert last["code"] == "pipeline_started"
    assert last["severity"] == "info"
    assert last["camera_id"] == "cam1"


def test_resource_thresholds_fire(tmp_path) -> None:
    engine = AlertEngine(
        AlertsConfig(
            enabled=True,
            log_path=str(tmp_path / "alerts.jsonl"),
            cooldown_seconds=0.0,
            gpu_temp_c_threshold=85.0,
            vram_pct_threshold=90.0,
            ram_pct_threshold=90.0,
        )
    )
    fired = engine.evaluate(
        camera_id="cam1",
        frame_id=3,
        correlation_id="abc",
        utilization_pct=0.0,
        slot_statuses={},
        health={"ingest": {"status": "HEALTHY"}, "model": {"status": "HEALTHY"}},
        system={
            "gpu": {
                "temperature_c": 86.0,
                "vram_percent": 95.0,
                "vram_used_mb": 7000.0,
                "vram_total_mb": 8192.0,
            },
            "ram": {"percent": 92.0, "used_mb": 29000.0, "total_mb": 31931.0},
        },
    )
    codes = {a["code"] for a in fired}
    assert {"gpu_temp_high", "vram_high", "ram_high"} <= codes


def test_resource_thresholds_quiet_when_disabled(tmp_path) -> None:
    engine = AlertEngine(
        AlertsConfig(
            enabled=True,
            log_path=str(tmp_path / "alerts.jsonl"),
            cooldown_seconds=0.0,
        )
    )
    fired = engine.evaluate(
        camera_id="cam1",
        frame_id=3,
        correlation_id="abc",
        utilization_pct=0.0,
        slot_statuses={},
        health={"ingest": {"status": "HEALTHY"}, "model": {"status": "HEALTHY"}},
        system={"gpu": {"temperature_c": 99.0, "vram_percent": 99.0},
                "ram": {"percent": 99.0}},
    )
    assert fired == []


def test_store_alert_ring_buffer() -> None:
    store = InspectorStateStore(max_alerts=3)
    for i in range(5):
        store.append_alert({"code": f"c{i}"})
    assert [a["code"] for a in store.alerts()] == ["c2", "c3", "c4"]
    assert [a["code"] for a in store.alerts(limit=2)] == ["c3", "c4"]
