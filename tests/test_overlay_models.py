from __future__ import annotations

import cv2
import numpy as np

from smart_parking.types import Detection, FrameContext
from smart_parking.ui.overlay import (
    DETR_COLOR,
    OTHER_COLOR,
    YOLO_COLOR,
    draw_overlay,
)


def _ctx(**kwargs) -> FrameContext:
    return FrameContext(
        frame_id=1,
        timestamp_ms=0.0,
        image=np.zeros((240, 320, 3), dtype=np.uint8),
        **kwargs,
    )


def _has_color(img: np.ndarray, color: tuple[int, int, int]) -> bool:
    mask = cv2.inRange(img, np.array(color), np.array(color))
    return bool((mask > 0).any())


def test_draws_detr_and_yolo_boxes() -> None:
    ctx = _ctx(
        detr_detections=[Detection((20, 40, 120, 200), 0.9, 1, "car")],
        yolo_detections=[Detection((160, 30, 300, 210), 0.7, 0, "person")],
    )
    out = draw_overlay(ctx, [])
    assert _has_color(out, DETR_COLOR)
    assert _has_color(out, YOLO_COLOR)


def test_single_model_falls_back_to_fused() -> None:
    ctx = _ctx(detections=[Detection((20, 40, 120, 200), 0.9, 1, "car")])
    out = draw_overlay(ctx, [])
    assert _has_color(out, OTHER_COLOR)
    assert not _has_color(out, DETR_COLOR)


def test_no_per_model_boxes_when_layers_disabled() -> None:
    out = draw_overlay(_ctx(), [])
    assert not _has_color(out, DETR_COLOR)
    assert not _has_color(out, YOLO_COLOR)
