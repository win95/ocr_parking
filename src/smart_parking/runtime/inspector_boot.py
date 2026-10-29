"""Start Pipeline Inspector in a background thread."""

from __future__ import annotations

import logging
import threading

from smart_parking.config import AppConfig

_log = logging.getLogger("smart_parking")


def start_inspector(cfg: AppConfig) -> None:
    if not cfg.inspector.enabled:
        return

    def _run() -> None:
        from smart_parking.api.inspector import run_inspector

        run_inspector(cfg.inspector)

    threading.Thread(target=_run, daemon=True).start()
    _log.info("Inspector http://%s:%s", cfg.inspector.host, cfg.inspector.port)
