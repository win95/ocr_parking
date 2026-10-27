"""Optional NVIDIA GPU utilization for pipeline baseline metrics."""

from __future__ import annotations


def read_gpu_utilization() -> tuple[float | None, float | None]:
    """Return (gpu_util_percent, vram_used_mb) or (None, None) if unavailable."""
    try:
        import pynvml  # type: ignore[import-untyped]

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        return float(util.gpu), mem.used / (1024 * 1024)
    except Exception:
        return None, None
