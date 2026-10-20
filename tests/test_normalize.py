import pytest

from smart_parking.detection.normalize import validate_bbox
from smart_parking.types import Detection
from smart_parking.detection.normalize import to_contract


def test_validate_bbox_clamp() -> None:
    bb = validate_bbox((-5, 0, 200, 50), 100, 100)
    assert bb[0] == 0 and bb[2] == 100


def test_invalid_bbox_raises() -> None:
    with pytest.raises(ValueError):
        validate_bbox((50, 50, 10, 60), 100, 100)


def test_to_contract() -> None:
    det = Detection((1, 2, 3, 4), 0.5, 2, "car")
    c = to_contract(det, "cam", 0, 0.0, "yolo", 100, 100)
    assert c.source == "yolo"
