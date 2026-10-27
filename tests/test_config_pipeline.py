import pytest

from smart_parking.config import (
    AppConfig,
    DetrConfig,
    FusionConfig,
    LayerFlags,
    PipelineConfig,
    load_config,
)
from smart_parking.detection.detr_r50 import torch_device


def test_detr_deploy_config() -> None:
    cfg = load_config("configs/deploy/server.detr.yaml")
    assert cfg.pipeline.layers.detr is True
    assert cfg.pipeline.layers.yolo is True
    assert cfg.pipeline.layers.fusion is True
    assert cfg.fusion.strategy == "union"
    assert cfg.detr.model_id == "facebook/detr-resnet-50-dc5"
    assert cfg.detr.size == 384
    # Demo shows every class of both models on the overlay.
    assert cfg.detr.vehicle_only is False
    assert cfg.yolo is not None and cfg.yolo.vehicle_only is False
    assert cfg.analytics.alerts.enabled is True
    assert cfg.analytics.alerts.gpu_temp_c_threshold == 85.0
    assert cfg.analytics.alerts.ram_pct_threshold == 90.0
    assert cfg.pipeline.max_fps == 5.0


def test_fps_cap_token_bucket() -> None:
    from smart_parking.app import _advance_tokens

    assert _advance_tokens(0.0, 0.1, 5.0) == 0.5
    assert _advance_tokens(0.8, 0.1, 5.0) == 1.3
    assert _advance_tokens(1.0, 10.0, 5.0) == 2.0
    assert _advance_tokens(0.5, -1.0, 5.0) == 0.5


def test_detr_device_alias() -> None:
    assert torch_device("0") == "cuda:0"
    assert torch_device("2") == "cuda:2"
    assert torch_device("cuda:1") == "cuda:1"
    assert torch_device("cpu") == "cpu"
    assert torch_device("") == "cpu"


def test_detr_default_size_is_paper_default() -> None:
    assert DetrConfig().size == 800


def test_fusion_requires_two_models() -> None:
    with pytest.raises(ValueError):
        AppConfig(
            pipeline=PipelineConfig(
                mode="normal",
                layers=LayerFlags(detr=False, yolo=True, fusion=True),
            ),
            fusion=FusionConfig(strategy="union"),
        )


def test_replay_disables_drop() -> None:
    cfg = AppConfig(pipeline=PipelineConfig(mode="replay"))
    assert cfg.pipeline.drop_frames_in_realtime is False
