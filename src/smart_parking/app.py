"""Application entry — delegates to runtime session."""

from __future__ import annotations

import logging
import os
import sys

from smart_parking.config import AppConfig
from smart_parking.runtime.session import run_ingest_session

_log = logging.getLogger("smart_parking")


def _display_available() -> bool:
    """Linux OpenCV Qt backend needs an X11/Wayland display server."""
    if not sys.platform.startswith("linux"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def run_app(cfg: AppConfig) -> None:
    """Main processing loop using modular pipeline."""
    logging.basicConfig(
        level=logging.INFO if cfg.pipeline.mode == "normal" else logging.DEBUG
    )
    if cfg.ui.enabled and not _display_available():
        _log.warning(
            "No DISPLAY/WAYLAND_DISPLAY detected — disabling local OpenCV UI. "
            "Set DISPLAY (e.g. DISPLAY=:0) to show the window."
        )
        cfg = cfg.model_copy(
            update={"ui": cfg.ui.model_copy(update={"enabled": False})}
        )
    run_ingest_session(cfg)
