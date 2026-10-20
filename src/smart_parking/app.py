"""Application pipeline wiring."""

from __future__ import annotations

import logging
import threading
import time

import cv2

from smart_parking.analytics import DEFAULT_WIDGETS, KPIEngine
from smart_parking.config import AppConfig
from smart_parking.ingest import FrameLoop, parse_source
from smart_parking.occupancy import load_slots
from smart_parking.pipeline.context import PipelineFrame
from smart_parking.pipeline.observability import new_correlation_id
from smart_parking.pipeline.runner import ModularPipeline
from smart_parking.replay.store import ArtifactStore
from smart_parking.types import SlotState
from smart_parking.ui import render_panel

_log = logging.getLogger("smart_parking")


def _start_inspector(cfg: AppConfig) -> None:
    if not cfg.inspector.enabled:
        return

    def _run() -> None:
        from smart_parking.api.inspector import run_inspector

        run_inspector(cfg.inspector.host, cfg.inspector.port)

    threading.Thread(target=_run, daemon=True).start()
    _log.info("Inspector http://%s:%s", cfg.inspector.host, cfg.inspector.port)


def run_app(cfg: AppConfig) -> None:
    """Main processing loop using modular pipeline."""
    logging.basicConfig(level=logging.INFO if cfg.pipeline.mode == "normal" else logging.DEBUG)
    slots = load_slots(cfg.slots_path)
    pipeline = ModularPipeline(cfg)
    kpi = KPIEngine(len(slots), cfg.analytics.log_path)
    artifacts = (
        ArtifactStore(cfg.artifacts.directory, cfg.artifacts.max_frames)
        if cfg.artifacts.enabled
        else None
    )
    _start_inspector(cfg)

    source = parse_source(cfg.source)
    source.open()
    loop = FrameLoop(
        source,
        max_queue=cfg.pipeline.queue_max,
        drop_when_busy=cfg.pipeline.drop_frames_in_realtime
        and cfg.pipeline.mode not in ("replay", "benchmark"),
        on_drop=pipeline.mark_dropped,
    )

    window = "Smart Parking"
    t_prev = time.perf_counter()
    fps = 0.0
    try:
        for raw in loop:
            pf = PipelineFrame(
                camera_id=cfg.pipeline.camera_id,
                frame_id=raw.frame_id,
                timestamp_ms=raw.timestamp_ms,
                correlation_id=new_correlation_id(),
                image=raw.image,
            )
            pf.fps = fps
            pf = pipeline.process(pf)
            legacy_states = {
                sid: SlotState(
                    slot_id=sid,
                    occupied=st.status.value == "OCCUPIED",
                    coasting=st.coasting,
                )
                for sid, st in pf.slot_states.items()
            }
            snapshot = kpi.update(legacy_states)

            if artifacts:
                artifacts.maybe_save(pf, cfg.artifacts.sample_every_n)

            now = time.perf_counter()
            dt = now - t_prev
            t_prev = now
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt)

            if not cfg.ui.enabled:
                continue
            vis = pf.overlay_image if pf.overlay_image is not None else raw.image
            if pf.minimap_image is not None:
                mw = max(1, vis.shape[1] // 4)
                mh = max(1, vis.shape[0] // 4)
                mm = cv2.resize(pf.minimap_image, (mw, mh))
                h, w = min(mh, vis.shape[0]), min(mw, vis.shape[1])
                vis[0:h, 0:w] = mm[0:h, 0:w]
            panel = render_panel(
                vis.shape[0],
                cfg.ui.panel_width,
                snapshot,
                DEFAULT_WIDGETS,
                fps,
                cfg.yolo.backend if cfg.yolo else "pytorch",
            )
            combined = cv2.hconcat([vis, panel])
            cv2.imshow(window, combined)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        source.close()
        if cfg.ui.enabled:
            cv2.destroyAllWindows()
