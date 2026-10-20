from smart_parking.config import SmoothingConfig
from smart_parking.tracking.smoother import SlotSmoother


def test_smoother_hysteresis() -> None:
    cfg = SmoothingConfig(window=5, t_on=3, t_off=3)
    sm = SlotSmoother(["s1"], cfg)
    for _ in range(3):
        sm.update({"s1": True})
    assert sm.update({"s1": True})["s1"].occupied
    for _ in range(5):
        out = sm.update({"s1": False})
    assert not out["s1"].occupied
