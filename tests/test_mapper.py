from smart_parking.occupancy.mapper import map_detections_to_slots
from smart_parking.occupancy.slots import Slot
from smart_parking.types import Detection


def test_mapper_center_in_slot() -> None:
    slots = [Slot(id="A", zone="Z", polygon=[(0, 0), (100, 0), (100, 100), (0, 100)])]
    det = Detection(
        bbox_xyxy=(40, 40, 60, 60),
        confidence=0.9,
        class_id=0,
        class_name="car",
    )
    raw = map_detections_to_slots([det], slots, {"car"})
    assert raw["A"] is True
