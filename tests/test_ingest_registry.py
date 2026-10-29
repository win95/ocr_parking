"""Tests for config-driven stream resolution."""

import pytest

from smart_parking.config import AppConfig, CameraConfig, PipelineConfig
from smart_parking.ingest.registry import (
    apply_active_source_override,
    effective_app_config,
    resolve_active_stream,
    resolve_streams,
)


def test_resolve_single_source_from_legacy_fields() -> None:
    cfg = AppConfig(source="data/sample.mp4", pipeline=PipelineConfig(camera_id="cam-a"))
    streams = resolve_streams(cfg)
    assert len(streams) == 1
    assert streams[0].id == "cam-a"
    assert streams[0].source == "data/sample.mp4"


def test_resolve_cameras_list_and_active() -> None:
    cfg = AppConfig(
        cameras=[
            CameraConfig(id="a", source="rtsp://10.0.0.1/a", slots_path="s/a.json"),
            CameraConfig(id="b", source="rtsp://10.0.0.1/b", slots_path="s/b.json"),
        ],
        active_camera="b",
    )
    active = resolve_active_stream(cfg)
    assert active.id == "b"
    assert active.slots_path == "s/b.json"


def test_effective_app_config_maps_active() -> None:
    cfg = AppConfig(
        source="data/old.mp4",
        cameras=[CameraConfig(id="x", source="rtsp://cam/x", slots_path="s/x.json")],
        active_camera="x",
        pipeline=PipelineConfig(camera_id="legacy"),
    )
    eff = effective_app_config(cfg)
    assert eff.source == "rtsp://cam/x"
    assert eff.slots_path == "s/x.json"
    assert eff.pipeline.camera_id == "x"


def test_cli_source_override_active_only() -> None:
    cfg = AppConfig(
        cameras=[
            CameraConfig(id="a", source="rtsp://old/a"),
            CameraConfig(id="b", source="rtsp://old/b"),
        ],
        active_camera="a",
    )
    updated = apply_active_source_override(cfg, "rtsp://new/a")
    assert resolve_active_stream(updated).source == "rtsp://new/a"
    assert resolve_streams(updated)[1].source == "rtsp://old/b"


def test_duplicate_camera_id_rejected() -> None:
    cfg = AppConfig(
        cameras=[
            CameraConfig(id="dup", source="rtsp://1"),
            CameraConfig(id="dup", source="rtsp://2"),
        ]
    )
    with pytest.raises(ValueError, match="duplicate"):
        resolve_streams(cfg)


def test_models_active_maps_detection() -> None:
    from smart_parking.config import ModelRegistryEntry, ModelsConfig

    cfg = AppConfig(
        models=ModelsConfig(
            active="prod",
            registry=[
                ModelRegistryEntry(
                    id="prod",
                    path="models/custom.pt",
                    backend="tensorrt",
                    status="approved",
                )
            ],
        )
    )
    assert cfg.detection.model_path == "models/custom.pt"
    assert cfg.detection.backend == "tensorrt"
