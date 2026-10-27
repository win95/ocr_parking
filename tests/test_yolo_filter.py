from smart_parking.detection.yolo_ultralytics import vehicle_allowed

VEHICLES = {"car", "truck", "bus", "motorcycle", "vehicle"}


def test_vehicle_class_kept() -> None:
    assert vehicle_allowed("car", VEHICLES) is True
    assert vehicle_allowed("truck", VEHICLES) is True
    assert vehicle_allowed("Motorcycle", VEHICLES) is True


def test_non_vehicle_class_dropped() -> None:
    assert vehicle_allowed("person", VEHICLES) is False
    assert vehicle_allowed("apple", VEHICLES) is False
    assert vehicle_allowed("surfboard", VEHICLES) is False


def test_empty_allow_list_keeps_everything() -> None:
    assert vehicle_allowed("person", set()) is True
    assert vehicle_allowed("car", set()) is True
