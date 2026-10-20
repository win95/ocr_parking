from smart_parking.config import OccupancyConfig, SmoothingConfig
from smart_parking.contracts import OccupancyStatus
from smart_parking.occupancy.engine import OccupancyEngine
from smart_parking.occupancy.slots import Slot
from smart_parking.pipeline.context import PipelineFrame
from smart_parking.types import Detection
import numpy as np


def test_stale_after_no_raw_detection() -> None:
    slots = [Slot("A", "Z", [(0, 0), (100, 0), (100, 100), (0, 100)])]
    cfg = OccupancyConfig(stale_after_ms=100.0)
    smooth = SmoothingConfig(window=5, t_on=1, t_off=4)
    eng = OccupancyEngine(slots, cfg, smooth)
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    det = Detection((40, 40, 60, 60), 0.9, 0, "car")

    f1 = PipelineFrame("c", 0, 0.0, "x", image=img)
    eng.update(f1, [det])
    assert f1.slot_states["A"].status == OccupancyStatus.OCCUPIED

    for i in range(2):
        f = PipelineFrame("c", i + 1, float(i + 1), "x", image=img)
        eng.update(f, [det])
    assert f.slot_states["A"].status == OccupancyStatus.OCCUPIED

    f3 = PipelineFrame("c", 3, 500.0, "x", image=img)
    eng.update(f3, [])
    assert f3.slot_states["A"].status == OccupancyStatus.STALE
