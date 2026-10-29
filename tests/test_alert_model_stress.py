"""Fire/smoke alert stream (slow frame + YOLO/DETR)."""

from smart_parking.analytics.alert_engine import AlertEngine
from smart_parking.analytics.fire_smoke_scanner import filter_hits
from smart_parking.config import AlertsConfig
from smart_parking.types import Detection


def test_filter_fire_smoke_hits() -> None:
    dets = [
        Detection((0, 0, 1, 1), 0.9, 0, "fire"),
        Detection((0, 0, 1, 1), 0.5, 1, "smoke"),
        Detection((0, 0, 1, 1), 0.9, 2, "car"),
    ]
    fire, smoke = filter_hits(
        dets,
        fire_labels={"fire"},
        smoke_labels={"smoke"},
        min_confidence=0.35,
    )
    assert len(fire) == 1
    assert len(smoke) == 1


def test_fire_smoke_alerts_per_model(tmp_path) -> None:
    log_path = tmp_path / "alerts.jsonl"
    engine = AlertEngine(
        AlertsConfig(
            enabled=True,
            log_path=str(log_path),
            cooldown_seconds=0.0,
            on_fire=True,
            on_smoke=True,
        )
    )
    fired = engine.evaluate_fire_smoke(
        camera_id="cam1",
        frame_id=10,
        correlation_id="fs-1",
        hits=[
            {"kind": "fire", "model": "yolo", "class_name": "fire", "confidence": 0.8},
            {"kind": "fire", "model": "detr", "class_name": "fire", "confidence": 0.7},
            {"kind": "smoke", "model": "yolo", "class_name": "smoke", "confidence": 0.6},
        ],
    )
    codes = {a["code"] for a in fired}
    assert "fire_detected" in codes
    assert "smoke_detected" in codes
    assert len(fired) == 3
    text = log_path.read_text(encoding="utf-8")
    assert '"channel": "fire_smoke"' in text
