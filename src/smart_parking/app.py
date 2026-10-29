"""Application entry — delegates to runtime session."""

from __future__ import annotations

import logging

from smart_parking.config import AppConfig
from smart_parking.runtime.session import run_ingest_session


def run_app(cfg: AppConfig) -> None:
    """Main processing loop using modular pipeline."""
    logging.basicConfig(
        level=logging.INFO if cfg.pipeline.mode == "normal" else logging.DEBUG
    )
    run_ingest_session(cfg)
