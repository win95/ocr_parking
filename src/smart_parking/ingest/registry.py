"""Resolve video streams from application config."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from smart_parking.config import AppConfig, CameraConfig
from smart_parking.ingest.sources import FrameSource, parse_source


@dataclass(frozen=True)
class ResolvedStream:
    """One ingest target after config resolution."""

    id: str
    source: str
    slots_path: str
    enabled: bool = True


def _validate_source_spec(value: str) -> str:
    if value.startswith(("webcam:", "rtsp://")):
        return value
    if ".." in Path(value).parts:
        raise ValueError("source path must not contain '..'")
    return value


def resolve_streams(cfg: AppConfig) -> list[ResolvedStream]:
    """Build the list of configured streams (may be multiple, MVP runs one active)."""
    if cfg.cameras:
        seen: set[str] = set()
        out: list[ResolvedStream] = []
        for cam in cfg.cameras:
            if cam.id in seen:
                raise ValueError(f"duplicate camera id: {cam.id}")
            seen.add(cam.id)
            out.append(
                ResolvedStream(
                    id=cam.id,
                    source=_validate_source_spec(cam.source),
                    slots_path=cam.slots_path,
                    enabled=cam.enabled,
                )
            )
        return out
    return [
        ResolvedStream(
            id=cfg.pipeline.camera_id,
            source=_validate_source_spec(cfg.source),
            slots_path=cfg.slots_path,
            enabled=True,
        )
    ]


def resolve_active_stream(cfg: AppConfig) -> ResolvedStream:
    """Pick the stream to open for the current run."""
    streams = resolve_streams(cfg)
    active_id = cfg.active_camera or cfg.pipeline.camera_id
    for stream in streams:
        if stream.id == active_id:
            if not stream.enabled:
                raise ValueError(f"camera {active_id} is disabled in config")
            return stream
    if len(streams) == 1 and streams[0].id == active_id:
        return streams[0]
    ids = ", ".join(s.id for s in streams)
    raise ValueError(f"active_camera {active_id!r} not in configured cameras: {ids}")


def apply_active_source_override(cfg: AppConfig, source_override: str | None) -> AppConfig:
    """Return config with active stream source replaced (CLI --source)."""
    if not source_override:
        return cfg
    active = resolve_active_stream(cfg)
    override = _validate_source_spec(source_override.strip())
    if cfg.cameras:
        updated: list[CameraConfig] = []
        for cam in cfg.cameras:
            if cam.id == active.id:
                updated.append(cam.model_copy(update={"source": override}))
            else:
                updated.append(cam)
        return cfg.model_copy(update={"cameras": updated, "source": override})
    return cfg.model_copy(update={"source": override})


def effective_app_config(cfg: AppConfig) -> AppConfig:
    """Map active stream fields onto top-level cfg for pipeline wiring."""
    active = resolve_active_stream(cfg)
    return cfg.model_copy(
        update={
            "source": active.source,
            "slots_path": active.slots_path,
            "pipeline": cfg.pipeline.model_copy(update={"camera_id": active.id}),
        }
    )


def open_frame_source(cfg: AppConfig, stream: ResolvedStream | None = None) -> FrameSource:
    """Parse and open the configured frame source."""
    spec = (stream or resolve_active_stream(cfg)).source
    source = parse_source(
        spec,
        rtsp_transport=cfg.ingest.rtsp_transport,
        connect_timeout_ms=cfg.ingest.connect_timeout_ms,
    )
    source.open()
    return source
