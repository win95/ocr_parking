"""Parking occupancy with FREE/OCCUPIED/UNKNOWN/STALE."""

from __future__ import annotations

import logging

from smart_parking.config import OccupancyConfig, SmoothingConfig
from smart_parking.contracts import OccupancyStatus, SlotStateContract
from smart_parking.occupancy.mapper import map_detections_to_slots
from smart_parking.occupancy.slots import Slot
from smart_parking.pipeline.context import PipelineFrame
from smart_parking.tracking.smoother import SlotSmoother
from smart_parking.types import Detection

_log = logging.getLogger("smart_parking")


class OccupancyEngine:
    """Maps detections to slots and applies temporal rules."""

    def __init__(
        self,
        slots: list[Slot],
        cfg: OccupancyConfig,
        smooth_cfg: SmoothingConfig,
    ) -> None:
        self._slots = slots
        self._cfg = cfg
        self._vehicle = {c.lower() for c in cfg.vehicle_classes}
        self._smoother = SlotSmoother([s.id for s in slots], smooth_cfg)
        self._last_raw_occupied_ms: dict[str, float] = {}
        self._size_checked = False

    def _check_frame_size(self, frame: PipelineFrame) -> None:
        if self._size_checked or not self._slots:
            return
        self._size_checked = True
        slot = self._slots[0]
        if not slot.meta_width or not slot.meta_height or frame.image is None:
            return
        height, width = frame.image.shape[:2]
        if (width, height) != (int(slot.meta_width), int(slot.meta_height)):
            _log.warning(
                "Slot calibration is %sx%s but incoming frame is %sx%s — "
                "occupancy polygons will be misaligned; recalibrate with "
                "scripts/calibrate_slots.py using a frame from this stream",
                int(slot.meta_width),
                int(slot.meta_height),
                width,
                height,
            )

    def update(self, frame: PipelineFrame, detections: list[Detection]) -> None:
        self._check_frame_size(frame)
        now = frame.timestamp_ms
        if not detections and self._cfg.unknown_on_empty:
            for slot in self._slots:
                frame.slot_states[slot.id] = SlotStateContract(
                    slot_id=slot.id,
                    status=OccupancyStatus.UNKNOWN,
                    reason="no_detections",
                    updated_at_ms=now,
                )
            return

        raw = map_detections_to_slots(detections, self._slots, self._vehicle)
        frame.raw_occupied = raw
        for sid, occ in raw.items():
            if occ:
                self._last_raw_occupied_ms[sid] = now

        smoothed = self._smoother.update(raw)
        stale_ms = self._cfg.stale_after_ms
        for sid, st in smoothed.items():
            status = OccupancyStatus.OCCUPIED if st.occupied else OccupancyStatus.FREE
            reason = "smoothed_vote"
            last_sig = self._last_raw_occupied_ms.get(sid, 0.0)
            if (
                st.occupied
                and not raw.get(sid, False)
                and last_sig > 0
                and (now - last_sig) > stale_ms
            ):
                status = OccupancyStatus.STALE
                reason = "no_recent_detection"
            frame.slot_states[sid] = SlotStateContract(
                slot_id=sid,
                status=status,
                confidence=1.0 if st.occupied else 0.0,
                reason=reason,
                updated_at_ms=now,
                coasting=st.coasting,
            )
