"""Draw slots and detections."""

from __future__ import annotations

import cv2
import numpy as np

from smart_parking.occupancy.slots import Slot
from smart_parking.types import Detection, FrameContext, SlotState


def _color_for(state: SlotState | None) -> tuple[int, int, int]:
    if state is None:
        return (128, 128, 128)
    if state.coasting:
        return (0, 255, 255)
    return (0, 0, 255) if state.occupied else (0, 255, 0)


def draw_overlay(
    ctx: FrameContext,
    slots: list[Slot],
    show_boxes: bool = True,
) -> np.ndarray:
    """Return annotated BGR image."""
    out = ctx.image.copy()
    for slot in slots:
        st = ctx.slot_states.get(slot.id)
        color = _color_for(st)
        pts = np.array(slot.polygon, dtype=np.int32)
        cv2.polylines(out, [pts], True, color, 2)
        label = slot.id
        if st and st.occupied:
            label += " OCC"
        cv2.putText(
            out,
            label,
            (int(pts[0][0]), int(pts[0][1]) - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
        )
    if show_boxes:
        for det in ctx.detections:
            x1, y1, x2, y2 = map(int, det.bbox_xyxy)
            cv2.rectangle(out, (x1, y1), (x2, y2), (255, 128, 0), 1)
    return out
