import pytest

from smart_parking.config import AppConfig, FusionConfig, LayerFlags, PipelineConfig


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
