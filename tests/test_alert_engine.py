"""Experimental alert JSONL logging."""

from __future__ import annotations

import json

from smart_parking.analytics.alert_engine import AlertEngine
from smart_parking.config import AlertsConfig


def test_ingest_degraded_logged(tmp_path) -> None:
    log_path = tmp_path / "alerts.jsonl"
    engine = AlertEngine(
        AlertsConfig(
            enabled=True,
            log_path=str(log_path),
            cooldown_seconds=0.0,
        )
    )
    fired = engine.evaluate(
        camera_id="cam1",
        frame_id=7,
        correlation_id="abc",
        utilization_pct=10.0,
        slot_statuses={},
        health={"ingest": {"status": "DEGRADED"}, "model": {"status": "HEALTHY"}},
    )
    assert len(fired) == 1
    assert fired[0]["code"] == "ingest_degraded"
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    row = json.loads(lines[0])
    assert row["frame_id"] == 7
    assert row["channel"] == "log"


def test_cooldown_suppresses_repeat(tmp_path) -> None:
    log_path = tmp_path / "alerts.jsonl"
    engine = AlertEngine(
        AlertsConfig(enabled=True, log_path=str(log_path), cooldown_seconds=3600.0)
    )
    health = {"ingest": {"status": "UNHEALTHY"}, "model": {"status": "HEALTHY"}}
    assert engine.evaluate(
        camera_id="c",
        frame_id=1,
        correlation_id="x",
        utilization_pct=0,
        slot_statuses={},
        health=health,
    )
    assert not engine.evaluate(
        camera_id="c",
        frame_id=2,
        correlation_id="y",
        utilization_pct=0,
        slot_statuses={},
        health=health,
    )
