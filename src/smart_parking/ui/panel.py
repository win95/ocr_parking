"""Analytics side panel."""

from __future__ import annotations

import cv2
import numpy as np

from smart_parking.analytics.widgets import KPIWidget


def render_panel(
    height: int,
    width: int,
    snapshot: dict,
    widgets: list[KPIWidget],
    fps: float,
    backend: str,
) -> np.ndarray:
    """Build BGR panel image."""
    panel = np.zeros((height, width, 3), dtype=np.uint8)
    panel[:] = (32, 32, 32)
    y = 28
    cv2.putText(panel, "Analytics", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    y += 28
    for w in widgets:
        line = f"{w.name()}: {w.value(snapshot)}"
        cv2.putText(panel, line, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        y += 22
    util = float(snapshot.get("utilization_pct", 0))
    bar_w = width - 24
    fill = int(bar_w * util / 100.0)
    cv2.rectangle(panel, (12, y), (12 + bar_w, y + 14), (80, 80, 80), -1)
    cv2.rectangle(panel, (12, y), (12 + fill, y + 14), (0, 180, 0), -1)
    y += 30
    cv2.putText(panel, f"FPS: {fps:.1f}", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 255), 1)
    y += 22
    cv2.putText(panel, f"Backend: {backend}", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1)
    return panel
