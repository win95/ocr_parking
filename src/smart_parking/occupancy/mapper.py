"""Map detections to parking slots."""

from __future__ import annotations

from smart_parking.occupancy.slots import Slot, point_in_polygon
from smart_parking.types import Detection


def bbox_center(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def map_detections_to_slots(
    detections: list[Detection],
    slots: list[Slot],
    vehicle_classes: set[str],
) -> dict[str, bool]:
    """Return raw per-slot occupancy for one frame."""
    occupied = {s.id: False for s in slots}
    for det in detections:
        if det.class_name.lower() not in vehicle_classes:
            continue
        cx, cy = bbox_center(det.bbox_xyxy)
        for slot in slots:
            if point_in_polygon(cx, cy, slot.polygon):
                occupied[slot.id] = True
    return occupied
