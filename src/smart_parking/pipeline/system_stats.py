"""Server-wide resource monitoring: GPU (nvidia-smi) + RAM/CPU (psutil)."""

from __future__ import annotations

import subprocess
import threading
import time
from typing import Any

import psutil

REFRESH_S = 1.0

_lock = threading.Lock()
_start_lock = threading.Lock()
_snapshot: dict[str, Any] | None = None
_thread: threading.Thread | None = None


def _mb(value: float) -> float:
    return round(float(value) / (1024 * 1024), 1)


def _gpu_nvidia_smi() -> dict[str, Any] | None:
    cmd = [
        "nvidia-smi",
        "--query-gpu="
        "utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,name",
        "--format=csv,noheader,nounits",
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=3, check=True
        )
    except Exception:
        return None
    line = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else ""
    if not line:
        return None
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 6:
        return None
    try:
        util = float(parts[0])
        used = float(parts[1])
        total = float(parts[2])
    except ValueError:
        return None
    return {
        "name": ",".join(parts[5:]).strip(),
        "util_percent": util,
        "vram_used_mb": used,
        "vram_total_mb": total,
        "vram_percent": round(used / total * 100.0, 1) if total else None,
        "temperature_c": _to_float(parts[3]),
        "power_w": _to_float(parts[4]),
    }


def _gpu_pynvml() -> dict[str, Any] | None:
    try:
        import pynvml  # type: ignore[import-untyped]

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode()
        total = _mb(mem.total)
        used = _mb(mem.used)
        return {
            "name": str(name),
            "util_percent": float(util.gpu),
            "vram_used_mb": used,
            "vram_total_mb": total,
            "vram_percent": round(used / total * 100.0, 1) if total else None,
            "temperature_c": _to_float(pynvml.nvmlDeviceGetTemperature(
                handle, pynvml.NVML_TEMPERATURE_GPU
            )),
            "power_w": None,
        }
    except Exception:
        return None


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _collect() -> dict[str, Any]:
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    try:
        load = list(psutil.getloadavg())
    except (AttributeError, OSError):
        load = None
    return {
        "ts": time.time(),
        "cpu_percent": psutil.cpu_percent(interval=None),
        "cpu_count": psutil.cpu_count(logical=True),
        "load_avg": load,
        "ram": {
            "total_mb": _mb(vm.total),
            "used_mb": _mb(vm.total - vm.available),
            "available_mb": _mb(vm.available),
            "percent": vm.percent,
        },
        "swap": {
            "total_mb": _mb(sw.total),
            "used_mb": _mb(sw.used),
            "percent": sw.percent,
        },
        "gpu": _gpu_nvidia_smi() or _gpu_pynvml(),
    }


def _loop() -> None:
    global _snapshot
    while True:
        snap = _collect()
        with _lock:
            _snapshot = snap
        time.sleep(REFRESH_S)


def system_snapshot() -> dict[str, Any]:
    """Latest server resources; samples in a background thread."""
    global _thread, _snapshot
    with _start_lock:
        if _thread is None or not _thread.is_alive():
            _thread = threading.Thread(
                target=_loop, name="system-stats", daemon=True
            )
            _thread.start()
    with _lock:
        snap = _snapshot
    if snap is None:
        snap = _collect()
        with _lock:
            _snapshot = snap
    return snap
