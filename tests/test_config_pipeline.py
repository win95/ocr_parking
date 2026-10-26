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
    assert cfg.pipeline.layers.yolo is False
    assert cfg.fusion.strategy == "detr_only"
    assert cfg.detr.model_id == "facebook/detr-resnet-50-dc5"
    assert cfg.detr.size == 384


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
