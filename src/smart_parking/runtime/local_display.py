"""Optional OpenCV local display (not used by web Inspector)."""

from __future__ import annotations

from pathlib import Path

import cv2

from smart_parking.analytics import DEFAULT_WIDGETS
from smart_parking.config import AppConfig
from smart_parking.pipeline.context import PipelineFrame
from smart_parking.types import FrameContext
from smart_parking.ui import render_panel


def compose_vis(pf: PipelineFrame, raw: FrameContext) -> cv2.Mat:
    vis = pf.overlay_image if pf.overlay_image is not None else raw.image
    if pf.minimap_image is not None:
        mw = max(1, vis.shape[1] // 4)
        mh = max(1, vis.shape[0] // 4)
        mm = cv2.resize(pf.minimap_image, (mw, mh))
        h, w = min(mh, vis.shape[0]), min(mw, vis.shape[1])
        vis[0:h, 0:w] = mm[0:h, 0:w]
    return vis


def save_alert_frame(save_dir: str, pf: PipelineFrame, raw: FrameContext, code: str) -> None:
    folder = Path(save_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{pf.camera_id}_{pf.frame_id:06d}_{code}.jpg"
    cv2.imwrite(str(path), compose_vis(pf, raw))


def save_alert_frame_from_raw(
    save_dir: str,
    camera_id: str,
    frame_id: int,
    correlation_id: str,
    image,
    code: str,
) -> None:
    folder = Path(save_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{camera_id}_{frame_id:06d}_{code}_{correlation_id[:8]}.jpg"
    cv2.imwrite(str(path), image)


def show_frame(
    cfg: AppConfig,
    pf: PipelineFrame,
    raw: FrameContext,
    snapshot: dict,
    fps: float,
    window: str = "Smart Parking",
) -> bool:
    """Render combined view; return False when user presses q."""
    vis = compose_vis(pf, raw)
    panel = render_panel(
        vis.shape[0],
        cfg.ui.panel_width,
        snapshot,
        DEFAULT_WIDGETS,
        fps,
        cfg.yolo.backend if cfg.yolo else "pytorch",
    )
    combined = cv2.hconcat([vis, panel])
    cv2.imshow(window, combined)
    return (cv2.waitKey(1) & 0xFF) != ord("q")
