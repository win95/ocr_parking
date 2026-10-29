"""Ingest session: open config-driven stream with reconnect."""

from __future__ import annotations

import logging
import time

import cv2

from smart_parking.analytics import AlertEngine, KPIEngine
from smart_parking.config import AppConfig
from smart_parking.ingest.registry import (
    effective_app_config,
    open_frame_source,
    resolve_active_stream,
    resolve_streams,
)
from smart_parking.ingest.sources import FrameSource, is_live_source
from smart_parking.ingest.telemetry import (
    configure_ingest,
    mark_connecting,
    mark_ingest_error,
    mark_stream_available,
    read_error_from_source,
    set_reconnect_count,
)
from smart_parking.occupancy import load_slots
from smart_parking.pipeline.observability import INSPECTOR_REGISTRY
from smart_parking.pipeline.runner import ModularPipeline
from smart_parking.replay.store import ArtifactStore
from smart_parking.runtime.alert_poll import AlertPollWorker
from smart_parking.runtime.frame_processor import StreamExitReason, consume_frames
from smart_parking.runtime.inspector_boot import start_inspector

_log = logging.getLogger("smart_parking")


def run_ingest_session(cfg: AppConfig) -> None:
    """Run reconnect loop for the active configured stream."""
    streams = resolve_streams(cfg)
    active = resolve_active_stream(cfg)
    run_cfg = effective_app_config(cfg)
    INSPECTOR_REGISTRY.configure_streams(
        streams,
        active.id,
        model_registry_id=cfg.models.active,
    )
    INSPECTOR_REGISTRY.set_active(active.id)

    slots = load_slots(run_cfg.slots_path)
    pipeline = ModularPipeline(run_cfg)
    kpi = KPIEngine(len(slots), run_cfg.analytics.log_path)
    alert_engine = (
        AlertEngine(run_cfg.analytics.alerts) if run_cfg.analytics.alerts.enabled else None
    )
    artifacts = (
        ArtifactStore(run_cfg.artifacts.directory, run_cfg.artifacts.max_frames)
        if run_cfg.artifacts.enabled
        else None
    )
    start_inspector(run_cfg)
    configure_ingest(
        active.source,
        run_cfg.ingest.stale_frame_ms,
        source_id=active.id,
    )
    set_reconnect_count(0)

    poll_worker: AlertPollWorker | None = None
    if alert_engine is not None:
        interval = min(15.0, max(2.0, run_cfg.analytics.alerts.cooldown_seconds / 2.0))
        poll_worker = AlertPollWorker(alert_engine, run_cfg.pipeline.camera_id, interval)
        poll_worker.start()

    fps_state = {"fps": 0.0, "t_prev": time.perf_counter()}
    live = is_live_source(active.source)
    reconnects = 0

    try:
        while True:
            source: FrameSource | None = None
            try:
                mark_connecting()
                source = open_frame_source(run_cfg, active)
                mark_stream_available()
                live = source.is_live
                exit_reason = consume_frames(
                    run_cfg, source, pipeline, kpi, artifacts, alert_engine, fps_state
                )
                if exit_reason is StreamExitReason.USER_QUIT:
                    _log.info("Stopped by user (UI quit)")
                    break
                read_err = read_error_from_source(source)
                if read_err:
                    mark_ingest_error(read_err)
                    if alert_engine is not None:
                        alert_engine.evaluate_from_store(run_cfg.pipeline.camera_id)
            except Exception as exc:
                mark_ingest_error(str(exc))
                if alert_engine is not None:
                    alert_engine.evaluate_from_store(run_cfg.pipeline.camera_id)
                _log.exception("Error while reading source %s", active.source)
            finally:
                if source is not None:
                    source.close()

            if not (live and run_cfg.ingest.reconnect):
                break
            next_reconnect = reconnects + 1
            if (
                run_cfg.ingest.max_reconnects is not None
                and next_reconnect > run_cfg.ingest.max_reconnects
            ):
                _log.error(
                    "Reconnect limit reached (%s), stopping",
                    run_cfg.ingest.max_reconnects,
                )
                break
            reconnects = next_reconnect
            set_reconnect_count(reconnects)
            _log.warning(
                "Source %s ended, reconnecting in %.1fs (attempt %s)",
                active.source,
                run_cfg.ingest.reconnect_delay_seconds,
                reconnects,
            )
            time.sleep(run_cfg.ingest.reconnect_delay_seconds)
    finally:
        if poll_worker is not None:
            poll_worker.stop()
        if run_cfg.ui.enabled:
            cv2.destroyAllWindows()
