from smart_parking.contracts import OccupancyStatus, SlotStateContract
from smart_parking.occupancy.slots import Slot
from smart_parking.pipeline.coasting import apply_track_coasting_to_slots
from smart_parking.types import Track


def test_coasting_applied_to_slot() -> None:
    slots = [Slot("A", "Z", [(0, 0), (100, 0), (100, 100), (0, 100)])]
    states = {
        "A": SlotStateContract(
            slot_id="A",
            status=OccupancyStatus.OCCUPIED,
            updated_at_ms=0,
        )
    }
    tracks = [
        Track(
            track_id=1,
            bbox_xyxy=(40, 40, 60, 60),
            confidence=0.5,
            coasting=True,
        )
    ]
    apply_track_coasting_to_slots(slots, states, tracks)
    assert states["A"].coasting is True
