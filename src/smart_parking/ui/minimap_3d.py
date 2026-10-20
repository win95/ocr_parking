"""Top-down minimap from canonical slot occupancy (image-space projection)."""

from __future__ import annotations

import cv2
import numpy as np

from smart_parking.contracts import OccupancyStatus, SlotStateContract
from smart_parking.occupancy.slots import Slot

_COLOR = {
    OccupancyStatus.FREE: (0, 180, 0),
    OccupancyStatus.OCCUPIED: (0, 0, 220),
    OccupancyStatus.UNKNOWN: (128, 128, 128),
    OccupancyStatus.STALE: (0, 165, 255),
}


def render_minimap(
    slots: list[Slot],
    states: dict[str, SlotStateContract],
    size: tuple[int, int] = (320, 240),
) -> np.ndarray:
    """Render 2D minimap; world coords = normalized slot centroids."""
    w, h = size
    canvas = np.zeros((h, w, 3), dtype=np.uint8)
    canvas[:] = (40, 40, 40)
    if not slots:
        return canvas
    xs = [p[0] for s in slots for p in s.polygon]
    ys = [p[1] for s in slots for p in s.polygon]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    def proj(x: float, y: float) -> tuple[int, int]:
        nx = (x - min_x) / (max_x - min_x + 1e-6)
        ny = (y - min_y) / (max_y - min_y + 1e-6)
        return int(nx * (w - 20) + 10), int(ny * (h - 20) + 10)

    for slot in slots:
        st = states.get(slot.id)
        status = st.status if st else OccupancyStatus.UNKNOWN
        color = _COLOR.get(status, (200, 200, 200))
        pts = np.array([proj(x, y) for x, y in slot.polygon], dtype=np.int32)
        cv2.fillPoly(canvas, [pts], color)
        cv2.polylines(canvas, [pts], True, (255, 255, 255), 1)
        cx = int(pts[:, 0].mean())
        cy = int(pts[:, 1].mean())
        cv2.putText(canvas, slot.id, (cx - 10, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)
    return canvas
