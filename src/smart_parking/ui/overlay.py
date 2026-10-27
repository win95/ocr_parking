"""Draw slots and detection boxes (per model when both models run)."""

from __future__ import annotations

import cv2
import numpy as np

from smart_parking.occupancy.slots import Slot
from smart_parking.types import Detection, FrameContext, SlotState

DETR_COLOR = (0, 140, 255)  # orange (BGR)
YOLO_COLOR = (255, 255, 0)  # cyan (BGR)
OTHER_COLOR = (255, 128, 0)

_FONT = cv2.FONT_HERSHEY_SIMPLEX


def _color_for(state: SlotState | None) -> tuple[int, int, int]:
    if state is None:
        return (128, 128, 128)
    if state.coasting:
        return (0, 255, 255)
    return (0, 0, 255) if state.occupied else (0, 255, 0)


def _draw_label(
    out: np.ndarray,
    text: str,
    x: int,
    y: int,
    color: tuple[int, int, int],
) -> None:
    """Filled caption above (or inside) the box top-left corner."""
    scale, thickness = 0.45, 1
    (tw, th), base = cv2.getTextSize(text, _FONT, scale, thickness)
    top = max(0, y - th - base - 4)
    cv2.rectangle(out, (x, top), (x + tw + 4, top + th + base + 2), color, -1)
    cv2.putText(
        out,
        text,
        (x + 2, top + th + 1),
        _FONT,
        scale,
        (0, 0, 0),
        thickness,
        cv2.LINE_AA,
    )


def _draw_detections(
    out: np.ndarray,
    detections: list[Detection],
    color: tuple[int, int, int],
    prefix: str,
) -> None:
    for det in detections:
        x1, y1, x2, y2 = (int(v) for v in det.bbox_xyxy)
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        _draw_label(
            out,
            f"{prefix} {det.class_name} {det.confidence:.2f}",
            x1,
            y1,
            color,
        )


def _draw_legend(
    out: np.ndarray,
    entries: list[tuple[str, tuple[int, int, int], int]],
) -> None:
    # Top-right: the minimap is composited over the top-left corner later.
    x = max(10, out.shape[1] - 110)
    y = 18
    for name, color, count in entries:
        cv2.rectangle(out, (x, y - 11), (x + 10, y - 1), color, -1)
        cv2.putText(
            out,
            f"{name}: {count}",
            (x + 16, y),
            _FONT,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        y += 20


def draw_overlay(
    ctx: FrameContext,
    slots: list[Slot],
    show_boxes: bool = True,
) -> np.ndarray:
    """Return annotated BGR image."""
    out = ctx.image.copy()
    for slot in slots:
        st = ctx.slot_states.get(slot.id)
        color = _color_for(st)
        pts = np.array(slot.polygon, dtype=np.int32)
        cv2.polylines(out, [pts], True, color, 2)
        label = slot.id
        if st and st.occupied:
            label += " OCC"
        cv2.putText(
            out,
            label,
            (int(pts[0][0]), int(pts[0][1]) - 4),
            _FONT,
            0.45,
            color,
            1,
        )
    if not show_boxes:
        return out

    legend: list[tuple[str, tuple[int, int, int], int]] = []
    if ctx.detr_detections is not None:
        _draw_detections(out, ctx.detr_detections, DETR_COLOR, "DETR")
        legend.append(("DETR", DETR_COLOR, len(ctx.detr_detections)))
    if ctx.yolo_detections is not None:
        _draw_detections(out, ctx.yolo_detections, YOLO_COLOR, "YOLO")
        legend.append(("YOLO", YOLO_COLOR, len(ctx.yolo_detections)))
    if not legend:
        # Single-model or legacy callers: show whatever the pipeline produced.
        _draw_detections(out, ctx.detections, OTHER_COLOR, "DET")
        legend.append(("DET", OTHER_COLOR, len(ctx.detections)))
    _draw_legend(out, legend)
    return out
