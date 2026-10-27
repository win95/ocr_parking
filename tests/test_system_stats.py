from smart_parking.pipeline.system_stats import _mb, _to_float, system_snapshot


def test_mb_conversion() -> None:
    assert _mb(1024 * 1024) == 1.0
    assert _mb(0) == 0.0


def test_to_float_handles_na() -> None:
    assert _to_float("81.19") == 81.19
    assert _to_float("N/A") is None
    assert _to_float(None) is None


def test_system_snapshot_has_memory_and_cpu() -> None:
    snap = system_snapshot()
    assert snap["ram"]["total_mb"] > 0
    assert 0.0 <= snap["ram"]["percent"] <= 100.0
    assert snap["ram"]["used_mb"] >= 0
    assert "swap" in snap
    assert snap["cpu_count"] and snap["cpu_count"] >= 1
    # GPU may legitimately be missing on machines without NVIDIA drivers.
    assert "gpu" in snap
