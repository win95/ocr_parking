from smart_parking.occupancy.slots import point_in_polygon


def test_point_in_square() -> None:
    square = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert point_in_polygon(5.0, 5.0, square)
    assert not point_in_polygon(15.0, 5.0, square)


def test_load_slots(tmp_path) -> None:
    from smart_parking.occupancy.slots import load_slots

    path = tmp_path / "s.json"
    path.write_text(
        '{"zones":[{"id":"A","zone":"Z","polygon":[[0,0],[1,0],[1,1]]}],'
        '"meta":{"width":100,"height":100}}',
        encoding="utf-8",
    )
    slots = load_slots(path)
    assert len(slots) == 1
    assert slots[0].id == "A"


def test_shipped_slots_wait_for_calibration() -> None:
    from smart_parking.occupancy.slots import load_slots

    slots = load_slots("configs/slots/parking_lot_01.json")
    assert slots == []


def test_zero_slots_are_safe() -> None:
    from smart_parking.analytics.kpi_engine import KPIEngine
    from smart_parking.ui.minimap_3d import render_minimap

    canvas = render_minimap([], {})
    assert canvas.shape == (240, 320, 3)

    kpi = KPIEngine(0, "/tmp/opencode/kpi_empty.jsonl")
    snapshot = kpi.update({})
    assert snapshot["total_slots"] == 0
    assert snapshot["utilization_pct"] == 0.0
    assert snapshot["occupied_count"] == 0
