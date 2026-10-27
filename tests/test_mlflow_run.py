"""MLflow experiment helpers (mocked)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from smart_parking.experiment.mlflow_run import DatasetRef, ExperimentRun, log_yaml_config


@pytest.fixture()
def mock_mlflow():
    with patch("smart_parking.experiment.mlflow_run._import_mlflow") as imp:
        mlflow = MagicMock()
        imp.return_value = mlflow
        yield mlflow


def test_experiment_run_logs_config_dataset_model(tmp_path: Path, mock_mlflow) -> None:
    cfg = tmp_path / "bench.yaml"
    cfg.write_text("pipeline:\n  mode: benchmark\n", encoding="utf-8")
    dataset = DatasetRef("ws/proj", "3", uri="/data/v3")

    with ExperimentRun(
        run_name="bench-1",
        experiment_name="smart-parking",
        config_path=cfg,
        dataset=dataset,
        model_version="yolo11n.pt",
    ) as run:
        run.log_metrics({"fps": 24.5})

    mock_mlflow.set_experiment.assert_called_once_with("smart-parking")
    mock_mlflow.start_run.assert_called_once_with(run_name="bench-1")
    mock_mlflow.log_artifact.assert_called()
    mock_mlflow.set_tag.assert_any_call("dataset", "ws/proj")
    mock_mlflow.set_tag.assert_any_call("dataset_version", "3")
    mock_mlflow.log_param.assert_any_call("model_version", "yolo11n.pt")
    mock_mlflow.log_metric.assert_called_with("fps", 24.5, step=None)
    mock_mlflow.end_run.assert_called_once()


def test_log_yaml_config_flattens_params(tmp_path: Path, mock_mlflow) -> None:
    cfg = tmp_path / "c.yaml"
    cfg.write_text("detection:\n  backend: pytorch\n", encoding="utf-8")
    log_yaml_config(cfg)
    mock_mlflow.log_param.assert_any_call("detection.backend", "pytorch")


def test_missing_mlflow_raises() -> None:
    with patch(
        "smart_parking.experiment.mlflow_run._import_mlflow",
        side_effect=RuntimeError("MLflow not installed"),
    ):
        with pytest.raises(RuntimeError, match="MLflow not installed"):
            with ExperimentRun(run_name="x"):
                pass
