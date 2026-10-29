"""Modular pipeline orchestrator."""

from __future__ import annotations

import time

import psutil

from smart_parking.config import AppConfig, FusionConfig
from smart_parking.contracts import PipelineMetrics, StageTiming
from smart_parking.detection.detr_r50 import DetrR50Detector
from smart_parking.detection.fusion import fuse_frame
from smart_parking.detection.normalize import batch_from_detections, detections_from_batch
from smart_parking.detection.tensorrt_runner import create_detector
from smart_parking.occupancy.engine import OccupancyEngine
from smart_parking.occupancy.slots import load_slots
from smart_parking.pipeline.coasting import apply_track_coasting_to_slots
from smart_parking.pipeline.context import PipelineFrame
from smart_parking.pipeline.gpu_stats import read_gpu_utilization
from smart_parking.pipeline.observability import get_inspector_store
from smart_parking.pipeline.stages.base import PipelineStage
from smart_parking.tracking.mot import SimpleTracker
from smart_parking.types import FrameContext, SlotState
from smart_parking.ui.minimap_3d import render_minimap
from smart_parking.ui.overlay import draw_overlay


class _DetrStage(PipelineStage):
    name = "detr"

    def __init__(self, enabled: bool, detector: DetrR50Detector | None) -> None:
        super().__init__(enabled)
        self._det = detector

    def _execute(self, frame: PipelineFrame) -> tuple[int, int]:
        if self._det is None:
            raise RuntimeError("DETR enabled but model unavailable")
        dets = self._det.detect(frame.image)
        frame.detr_batch = batch_from_detections(
            dets,
            frame.camera_id,
            frame.frame_id,
            frame.timestamp_ms,
            "detr",
            frame.image_width,
            frame.image_height,
        )
        return 1, len(dets)


class _YoloStage(PipelineStage):
    name = "yolo"

    def __init__(self, enabled: bool, detector) -> None:
        super().__init__(enabled)
        self._det = detector

    def _execute(self, frame: PipelineFrame) -> tuple[int, int]:
        if self._det is None:
            raise RuntimeError("YOLO enabled but model unavailable")
        dets = self._det.detect(frame.image)
        frame.yolo_batch = batch_from_detections(
            dets,
            frame.camera_id,
            frame.frame_id,
            frame.timestamp_ms,
            "yolo",
            frame.image_width,
            frame.image_height,
        )
        return 1, len(dets)


def _select_detections_without_fusion(
    frame: PipelineFrame,
    strategy: str,
) -> list:
    if strategy == "detr_only" and frame.detr_batch:
        return detections_from_batch(frame.detr_batch)
    if frame.yolo_batch:
        return detections_from_batch(frame.yolo_batch)
    if frame.detr_batch:
        return detections_from_batch(frame.detr_batch)
    return []


class ModularPipeline:
    """Runs enabled stages with metrics and inspector hooks."""

    def __init__(self, cfg: AppConfig) -> None:
        self._cfg = cfg
        self._slots = load_slots(cfg.slots_path)
        self._dropped = 0
        self._yolo = create_detector(cfg.yolo) if cfg.pipeline.layers.yolo else None
        self._detr: DetrR50Detector | None = None
        detr_layer = cfg.pipeline.layers.detr
        if detr_layer:
            if DetrR50Detector.is_available():
                self._detr = DetrR50Detector(cfg.detr)
            elif cfg.pipeline.mode != "benchmark":
                raise RuntimeError("DETR layer enabled but transformers not installed")
            else:
                detr_layer = False
        self._occupancy = OccupancyEngine(
            self._slots, cfg.occupancy, cfg.smoothing
        )
        self._tracker = SimpleTracker(cfg.tracking)
        self._stages: list[PipelineStage] = [
            _DetrStage(detr_layer, self._detr),
            _YoloStage(cfg.pipeline.layers.yolo, self._yolo),
        ]
        get_inspector_store(cfg.pipeline.camera_id).snapshot.config_mode = cfg.pipeline.mode

    def process(self, frame: PipelineFrame) -> PipelineFrame:
        store = get_inspector_store(frame.camera_id)
        frame.ensure_dims()
        timings: list[StageTiming] = []
        stage_failed = False
        for stage in self._stages:
            t = stage.run(frame)
            timings.append(t)
            store.set_layer(stage.name, stage.health(t))
            if stage.enabled and stage.name in ("yolo", "detr"):
                store.record_model_inference(
                    frame.timestamp_ms, t.ok, t.error
                )
            if stage.enabled and not t.ok:
                stage_failed = True
                if self._cfg.pipeline.mode == "debug":
                    from smart_parking.pipeline.observability import log_stage

                    log_stage(
                        frame.correlation_id,
                        frame.camera_id,
                        frame.frame_id,
                        stage.name,
                        "ERROR",
                        t.error or "stage failed",
                    )

        if stage_failed and self._cfg.pipeline.stop_on_stage_error:
            frame.detections = []
            frame.extra["pipeline_halted"] = True
        else:
            fused, fusion_timing = self._run_fusion(frame)
            timings.append(fusion_timing)
            frame.detections = fused

        if not frame.detections and frame.extra.get("pipeline_halted"):
            pass
        elif self._cfg.pipeline.layers.tracking:
            t0 = time.perf_counter()
            frame.tracks = self._tracker.update(frame.detections)
            timings.append(
                self._timing("tracking", t0, len(frame.detections), len(frame.tracks), True, None)
            )
        if self._cfg.pipeline.layers.occupancy and not frame.extra.get("pipeline_halted"):
            t0 = time.perf_counter()
            occ_ok = True
            occ_err: str | None = None
            try:
                self._occupancy.update(frame, frame.detections)
                if self._cfg.pipeline.layers.tracking:
                    apply_track_coasting_to_slots(
                        self._slots, frame.slot_states, frame.tracks
                    )
            except Exception as exc:
                occ_ok = False
                occ_err = str(exc)
            store.record_occupancy_update(
                frame.timestamp_ms, occ_ok, occ_err
            )
            timings.append(
                self._timing(
                    "occupancy",
                    t0,
                    len(frame.detections),
                    len(frame.slot_states),
                    occ_ok,
                    occ_err,
                )
            )
        if self._cfg.pipeline.layers.overlay:
            t0 = time.perf_counter()
            frame.overlay_image = self._render_overlay(frame)
            timings.append(self._timing("overlay", t0, 1, 1, True, None))

        if self._cfg.pipeline.layers.minimap:
            t0 = time.perf_counter()
            frame.minimap_image = render_minimap(self._slots, frame.slot_states)
            timings.append(self._timing("minimap", t0, 1, 1, True, None))

        gpu_util, vram_mb = read_gpu_utilization()
        metrics = PipelineMetrics(
            correlation_id=frame.correlation_id,
            camera_id=frame.camera_id,
            frame_id=frame.frame_id,
            timestamp_ms=frame.timestamp_ms,
            fps=frame.fps,
            dropped_frames=self._dropped,
            queue_depth=int(frame.extra.get("queue_depth", 0)),
            stages=timings,
            ram_mb=psutil.Process().memory_info().rss / (1024 * 1024),
            gpu_util=gpu_util,
            vram_mb=vram_mb,
        )
        frame.metrics = metrics
        store.update_metrics(metrics)
        store.snapshot.fusion_disagreements = frame.fusion_disagreements
        return frame

    def _run_fusion(self, frame: PipelineFrame) -> tuple[list, StageTiming]:
        t0 = time.perf_counter()
        if not self._cfg.pipeline.layers.fusion:
            fused = _select_detections_without_fusion(
                frame, self._cfg.fusion.strategy
            )
            timing = self._timing("fusion", t0, 1, len(fused), True, None)
            return fused, timing
        fused = fuse_frame(frame, self._cfg.fusion)
        frame.fused_batch = batch_from_detections(
            fused,
            frame.camera_id,
            frame.frame_id,
            frame.timestamp_ms,
            "fused",
            frame.image_width,
            frame.image_height,
        )
        timing = self._timing("fusion", t0, 2, len(fused), True, None)
        return fused, timing

    def _render_overlay(self, frame: PipelineFrame):
        legacy_slots = {
            k: SlotState(
                slot_id=k,
                occupied=v.status.value == "OCCUPIED",
                coasting=v.coasting,
            )
            for k, v in frame.slot_states.items()
        }
        ctx = FrameContext(
            frame_id=frame.frame_id,
            timestamp_ms=frame.timestamp_ms,
            image=frame.image,
            detections=frame.detections,
            slot_states=legacy_slots,
            tracks=frame.tracks,
            fps=frame.fps,
        )
        return draw_overlay(ctx, self._slots)

    @staticmethod
    def _timing(
        name: str,
        t0: float,
        inp: int,
        out: int,
        ok: bool,
        err: str | None,
    ) -> StageTiming:
        ms = (time.perf_counter() - t0) * 1000.0
        return StageTiming(
            stage=name, duration_ms=ms, ok=ok, error=err, input_count=inp, output_count=out
        )

    def mark_dropped(self) -> None:
        self._dropped += 1
