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
