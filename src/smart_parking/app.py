"""Application pipeline wiring."""

from __future__ import annotations

import logging
import threading
import time

import cv2

from smart_parking.analytics import DEFAULT_WIDGETS, AlertEngine, KPIEngine
from smart_parking.config import AppConfig
from smart_parking.ingest import FrameLoop, is_live_source, parse_source
from smart_parking.ingest.sources import FrameSource
from smart_parking.ingest.telemetry import (
    configure_ingest,
    mark_connecting,
    mark_frame_received,
    mark_ingest_error,
    mark_pipeline_processed,
    mark_stream_available,
    read_error_from_source,
    set_reconnect_count,
)
from smart_parking.occupancy import load_slots
from smart_parking.pipeline.context import PipelineFrame
from smart_parking.pipeline.observability import new_correlation_id
from smart_parking.pipeline.runner import ModularPipeline
from smart_parking.pipeline.system_stats import system_snapshot
from smart_parking.replay.store import ArtifactStore
from smart_parking.types import SlotState
from smart_parking.ui import render_panel

_log = logging.getLogger("smart_parking")


def _advance_tokens(tokens: float, dt: float, max_fps: float) -> float:
    """Token bucket so the average rate matches max_fps without wasting frames."""
    return min(2.0, tokens + max(0.0, dt) * max_fps)


def _compose_vis(pf: PipelineFrame, raw) -> "cv2.Mat":
    vis = pf.overlay_image if pf.overlay_image is not None else raw.image
    if pf.minimap_image is not None:
        mw = max(1, vis.shape[1] // 4)
        mh = max(1, vis.shape[0] // 4)
        mm = cv2.resize(pf.minimap_image, (mw, mh))
        h, w = min(mh, vis.shape[0]), min(mw, vis.shape[1])
        vis[0:h, 0:w] = mm[0:h, 0:w]
    return vis


def _save_alert_frame(save_dir: str, pf: PipelineFrame, raw, code: str) -> None:
    from pathlib import Path

    folder = Path(save_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{pf.camera_id}_{pf.frame_id:06d}_{code}.jpg"
    cv2.imwrite(str(path), _compose_vis(pf, raw))


def _start_inspector(cfg: AppConfig) -> None:
    if not cfg.inspector.enabled:
        return

    def _run() -> None:
        from smart_parking.api.inspector import run_inspector

        run_inspector(cfg.inspector.host, cfg.inspector.port)

    threading.Thread(target=_run, daemon=True).start()
    _log.info("Inspector http://%s:%s", cfg.inspector.host, cfg.inspector.port)


def _open_source(cfg: AppConfig) -> FrameSource:
    """Open the configured video source."""
    source = parse_source(
        cfg.source,
        rtsp_transport=cfg.ingest.rtsp_transport,
        connect_timeout_ms=cfg.ingest.connect_timeout_ms,
    )
    source.open()
    return source


def _consume_frames(
    cfg: AppConfig,
    source: FrameSource,
    pipeline: ModularPipeline,
    kpi: KPIEngine,
    artifacts: ArtifactStore | None,
    alerts: AlertEngine | None,
    fps_state: dict,
) -> None:
    """Process frames until the source is exhausted."""
    loop = FrameLoop(
        source,
        max_queue=cfg.pipeline.queue_max,
        drop_when_busy=cfg.pipeline.drop_frames_in_realtime
        and cfg.pipeline.mode not in ("replay", "benchmark"),
        on_drop=pipeline.mark_dropped,
    )

    window = "Smart Parking"
    max_fps = cfg.pipeline.max_fps or 0.0
    tokens = 1.0
    last_tick = time.perf_counter()
    for raw in loop:
        mark_frame_received(raw.timestamp_ms)
        if max_fps > 0.0:
            now = time.perf_counter()
            tokens = _advance_tokens(tokens, now - last_tick, max_fps)
            last_tick = now
            if tokens < 1.0:
                pipeline.mark_dropped()
                continue
            tokens -= 1.0
        pf = PipelineFrame(
            camera_id=cfg.pipeline.camera_id,
            frame_id=raw.frame_id,
            timestamp_ms=raw.timestamp_ms,
            correlation_id=new_correlation_id(),
            image=raw.image,
        )
        pf.fps = fps_state["fps"]
        pf = pipeline.process(pf)
        mark_pipeline_processed(pf.timestamp_ms, pf.frame_id)
        legacy_states = {
            sid: SlotState(
                slot_id=sid,
                occupied=st.status.value == "OCCUPIED",
                coasting=st.coasting,
            )
            for sid, st in pf.slot_states.items()
        }
        snapshot = kpi.update(legacy_states)

        if alerts is not None:
            from smart_parking.pipeline.observability import INSPECTOR_STORE

            health = INSPECTOR_STORE.to_dict()
            slot_statuses = {sid: st.status.value for sid, st in pf.slot_states.items()}
            fired = alerts.evaluate(
                camera_id=pf.camera_id,
                frame_id=pf.frame_id,
                correlation_id=pf.correlation_id,
                utilization_pct=float(snapshot.get("utilization_pct", 0)),
                slot_statuses=slot_statuses,
                health=health,
                system=system_snapshot(),
            )
            save_dir = cfg.analytics.alerts.save_frame_dir
            if fired and save_dir:
                _save_alert_frame(save_dir, pf, raw, fired[0]["code"])

        if artifacts:
            artifacts.maybe_save(pf, cfg.artifacts.sample_every_n)

        now = time.perf_counter()
        dt = now - fps_state["t_prev"]
        fps_state["t_prev"] = now
        if dt > 0:
            fps_state["fps"] = 0.9 * fps_state["fps"] + 0.1 * (1.0 / dt)

        if not cfg.ui.enabled:
            continue
        vis = _compose_vis(pf, raw)
        panel = render_panel(
            vis.shape[0],
            cfg.ui.panel_width,
            snapshot,
            DEFAULT_WIDGETS,
            fps_state["fps"],
            cfg.yolo.backend if cfg.yolo else "pytorch",
        )
        combined = cv2.hconcat([vis, panel])
        cv2.imshow(window, combined)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break


def run_app(cfg: AppConfig) -> None:
    """Main processing loop using modular pipeline."""
    logging.basicConfig(level=logging.INFO if cfg.pipeline.mode == "normal" else logging.DEBUG)
    slots = load_slots(cfg.slots_path)
    pipeline = ModularPipeline(cfg)
    kpi = KPIEngine(len(slots), cfg.analytics.log_path)
    alert_engine = (
        AlertEngine(cfg.analytics.alerts) if cfg.analytics.alerts.enabled else None
    )
    if alert_engine is not None:
        alert_engine.notify(
            "pipeline_started",
            "info",
            {
                "source": cfg.source,
                "camera_id": cfg.pipeline.camera_id,
                "detr": cfg.pipeline.layers.detr,
                "yolo": cfg.pipeline.layers.yolo,
                "fusion": cfg.pipeline.layers.fusion,
            },
            camera_id=cfg.pipeline.camera_id,
        )
    artifacts = (
        ArtifactStore(cfg.artifacts.directory, cfg.artifacts.max_frames)
        if cfg.artifacts.enabled
        else None
    )
    _start_inspector(cfg)
    configure_ingest(
        cfg.source,
        cfg.ingest.stale_frame_ms,
        source_id=cfg.pipeline.camera_id,
    )
    set_reconnect_count(0)

    fps_state = {"fps": 0.0, "t_prev": time.perf_counter()}
    live = is_live_source(cfg.source)
    reconnects = 0

    try:
        while True:
            source: FrameSource | None = None
            try:
                mark_connecting()
                source = _open_source(cfg)
                mark_stream_available()
                live = source.is_live
                _consume_frames(cfg, source, pipeline, kpi, artifacts, alert_engine, fps_state)
                read_err = read_error_from_source(source)
                if read_err:
                    mark_ingest_error(read_err)
            except Exception as exc:
                mark_ingest_error(str(exc))
                _log.exception("Error while reading source %s", cfg.source)
            finally:
                if source is not None:
                    source.close()

            if not (live and cfg.ingest.reconnect):
                break
            next_reconnect = reconnects + 1
            if (
                cfg.ingest.max_reconnects is not None
                and next_reconnect > cfg.ingest.max_reconnects
            ):
                _log.error("Reconnect limit reached (%s), stopping", cfg.ingest.max_reconnects)
                break
            reconnects = next_reconnect
            set_reconnect_count(reconnects)
            _log.warning(
                "Source %s ended, reconnecting in %.1fs (attempt %s)",
                cfg.source,
                cfg.ingest.reconnect_delay_seconds,
                reconnects,
            )
            time.sleep(cfg.ingest.reconnect_delay_seconds)
    finally:
        if cfg.ui.enabled:
            cv2.destroyAllWindows()
