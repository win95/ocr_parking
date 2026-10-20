"""Apply MOT coasting flags to slot occupancy contracts."""

from __future__ import annotations

from smart_parking.contracts import SlotStateContract
from smart_parking.occupancy.slots import Slot, point_in_polygon
from smart_parking.types import Track


def apply_track_coasting_to_slots(
    slots: list[Slot],
    states: dict[str, SlotStateContract],
    tracks: list[Track],
) -> None:
    for st in states.values():
        st.coasting = False
    for tr in tracks:
        if not tr.coasting:
            continue
        cx = (tr.bbox_xyxy[0] + tr.bbox_xyxy[2]) / 2
        cy = (tr.bbox_xyxy[1] + tr.bbox_xyxy[3]) / 2
        for slot in slots:
            if point_in_polygon(cx, cy, slot.polygon) and slot.id in states:
                states[slot.id].coasting = True
