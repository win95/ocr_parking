"""Process one frame through pipeline, KPI, alerts, and inspector state."""

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import TYPE_CHECKING

import cv2

from smart_parking.analytics import AlertEngine, KPIEngine
from smart_parking.config import AppConfig
from smart_parking.ingest.frame_loop import FrameLoop
from smart_parking.pipeline.context import PipelineFrame
from smart_parking.pipeline.frame_sample_buffer import FrameSampleBuffer
from smart_parking.pipeline.observability import get_inspector_store, new_correlation_id
from smart_parking.pipeline.runner import ModularPipeline
from smart_parking.replay.store import ArtifactStore
from smart_parking.runtime.local_display import save_alert_frame, show_frame
from smart_parking.types import SlotState

if TYPE_CHECKING:
    from smart_parking.ingest.sources import FrameSource

_log = logging.getLogger("smart_parking")


class StreamExitReason(str, Enum):
    STREAM_ENDED = "stream_ended"
    USER_QUIT = "user_quit"


def consume_frames(
    cfg: AppConfig,
    source: FrameSource,
    pipeline: ModularPipeline,
    kpi: KPIEngine,
    artifacts: ArtifactStore | None,
    alerts: AlertEngine | None,
    fps_state: dict,
    fire_smoke_buffer: FrameSampleBuffer | None = None,
) -> StreamExitReason:
    """Process frames until the source is exhausted or UI quit."""
    read_timeout = cfg.ingest.read_timeout_ms if source.is_live else None
    loop = FrameLoop(
        source,
        max_queue=cfg.pipeline.queue_max,
        drop_when_busy=cfg.pipeline.drop_frames_in_realtime
        and cfg.pipeline.mode not in ("replay", "benchmark"),
        on_drop=pipeline.mark_dropped,
        read_timeout_ms=read_timeout,
    )
    from smart_parking.ingest.telemetry import mark_frame_received, mark_pipeline_processed

    window = "Smart Parking"
    ui_enabled = cfg.ui.enabled
    for raw in loop:
        mark_frame_received(raw.timestamp_ms)
        if fire_smoke_buffer is not None:
            fire_smoke_buffer.offer(raw.frame_id, raw.timestamp_ms, raw.image)
        pf = PipelineFrame(
            camera_id=cfg.pipeline.camera_id,
            frame_id=raw.frame_id,
            timestamp_ms=raw.timestamp_ms,
            correlation_id=new_correlation_id(),
            image=raw.image,
        )
        pf.fps = fps_state["fps"]
        pf.extra["queue_depth"] = loop.queue_depth
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
        slot_statuses = {sid: st.status.value for sid, st in pf.slot_states.items()}

        fired_count = 0
        if alerts is not None:
            store = get_inspector_store(pf.camera_id)
            health = store.to_dict()
            fired = alerts.evaluate(
                camera_id=pf.camera_id,
                frame_id=pf.frame_id,
                correlation_id=pf.correlation_id,
                utilization_pct=float(snapshot.get("utilization_pct", 0)),
                slot_statuses=slot_statuses,
                health=health,
            )
            fired_count = len(fired)
            save_dir = cfg.analytics.alerts.save_frame_dir
            if fired and save_dir:
                save_alert_frame(save_dir, pf, raw, fired[0]["code"])

        store = get_inspector_store(pf.camera_id)
        store.set_last_alert_context(
            {
                "frame_id": pf.frame_id,
                "correlation_id": pf.correlation_id,
                "utilization_pct": float(snapshot.get("utilization_pct", 0)),
                "slot_statuses": slot_statuses,
            }
        )
        _update_current_frame(pf, fired_count)

        if artifacts:
            artifacts.maybe_save(pf, cfg.artifacts.sample_every_n)

        now = time.perf_counter()
        dt = now - fps_state["t_prev"]
        fps_state["t_prev"] = now
        if dt > 0:
            fps_state["fps"] = 0.9 * fps_state["fps"] + 0.1 * (1.0 / dt)

        if not ui_enabled:
            continue
        try:
            if not show_frame(cfg, pf, raw, snapshot, fps_state["fps"], window):
                return StreamExitReason.USER_QUIT
        except cv2.error as exc:
            _log.warning("Local UI disabled after OpenCV display error: %s", exc)
            ui_enabled = False

    return StreamExitReason.STREAM_ENDED


def _update_current_frame(pf: PipelineFrame, alerts_this_frame: int) -> None:
    counts: dict[str, int] = {}
    for st in pf.slot_states.values():
        key = st.status.value
        counts[key] = counts.get(key, 0) + 1
    get_inspector_store(pf.camera_id).set_current_frame(
        {
            "frame_id": pf.frame_id,
            "correlation_id": pf.correlation_id,
            "timestamp_ms": pf.timestamp_ms,
            "slot_counts": counts,
            "alerts_this_frame": alerts_this_frame,
        }
    )
