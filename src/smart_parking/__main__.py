"""CLI entry point."""

from __future__ import annotations

import argparse

from smart_parking.app import run_app
from smart_parking.config import load_config


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smart Parking Analytics")
    parser.add_argument("--config", default=None, help="Path to YAML config")
    parser.add_argument("--source", default=None, help="Override video, webcam:N, or rtsp://")
    parser.add_argument("--backend", default=None, choices=["pytorch", "tensorrt"])
    parser.add_argument(
        "--inspector-only",
        action="store_true",
        help="Run Pipeline Inspector API without video loop",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    cfg = load_config(args.config)
    if args.source:
        cfg = cfg.model_copy(update={"source": args.source})
    if args.backend and cfg.yolo:
        yolo = cfg.yolo.model_copy(update={"backend": args.backend})
        cfg = cfg.model_copy(update={"yolo": yolo, "detection": yolo})
    if args.inspector_only:
        cfg = cfg.model_copy(
            update={"inspector": cfg.inspector.model_copy(update={"enabled": True})}
        )
        from smart_parking.api.inspector import run_inspector

        run_inspector(cfg.inspector.host, cfg.inspector.port)
        return
    run_app(cfg)


if __name__ == "__main__":
    main()
