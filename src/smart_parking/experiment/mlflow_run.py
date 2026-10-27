"""MLflow helpers for benchmark and training runs."""

from __future__ import annotations

import os
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def _import_mlflow():
    try:
        import mlflow
    except ImportError as exc:
        raise RuntimeError(
            "MLflow not installed. Run: pip install -e '.[mlflow]'"
        ) from exc
    return mlflow


@dataclass(frozen=True)
class DatasetRef:
    """Dataset identity for experiment tags."""

    name: str
    version: str
    uri: str | None = None


class ExperimentRun(AbstractContextManager):
    """Context manager: one MLflow run per benchmark or training job."""

    def __init__(
        self,
        run_name: str,
        experiment_name: str | None = None,
        config_path: str | Path | None = None,
        dataset: DatasetRef | None = None,
        model_version: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        self._run_name = run_name
        self._experiment = experiment_name or os.environ.get(
            "MLFLOW_EXPERIMENT_NAME", "smart-parking"
        )
        self._config_path = Path(config_path) if config_path else None
        self._dataset = dataset
        self._model_version = model_version
        self._tags = tags or {}
        self._mlflow: Any = None
        self._active = False

    def __enter__(self) -> ExperimentRun:
        mlflow = _import_mlflow()
        mlflow.set_experiment(self._experiment)
        mlflow.start_run(run_name=self._run_name)
        self._mlflow = mlflow
        self._active = True
        self._log_metadata()
        return self

    def __exit__(self, *exc: object) -> None:
        if self._active and self._mlflow is not None:
            self._mlflow.end_run()
        self._active = False

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        log_run_metrics(metrics, step=step)

    def log_artifact(self, path: str | Path, artifact_path: str = "") -> None:
        if self._mlflow is None:
            return
        self._mlflow.log_artifact(str(path), artifact_path=artifact_path)

    def _log_metadata(self) -> None:
        if self._config_path and self._config_path.is_file():
            log_yaml_config(self._config_path)
        if self._dataset:
            log_dataset_ref(self._dataset)
        if self._model_version:
            self._mlflow.log_param("model_version", self._model_version)
        for key, value in self._tags.items():
            self._mlflow.set_tag(key, value)


def log_yaml_config(path: Path) -> None:
    """Store full YAML and scalar params extracted from top-level keys."""
    mlflow = _import_mlflow()
    mlflow.log_artifact(str(path), artifact_path="config")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    mlflow.log_param("config_file", path.name)
    _log_flat_params(data, prefix="")


def log_dataset_ref(dataset: DatasetRef) -> None:
    mlflow = _import_mlflow()
    mlflow.set_tag("dataset", dataset.name)
    mlflow.set_tag("dataset_version", dataset.version)
    if dataset.uri:
        mlflow.log_param("dataset_uri", dataset.uri)


def log_model_info(model_path: str, backend: str, extra: dict[str, str] | None = None) -> None:
    mlflow = _import_mlflow()
    mlflow.log_param("model_path", model_path)
    mlflow.log_param("model_backend", backend)
    for key, value in (extra or {}).items():
        mlflow.log_param(key, value)


def log_run_metrics(metrics: dict[str, float], step: int | None = None) -> None:
    mlflow = _import_mlflow()
    for key, value in metrics.items():
        mlflow.log_metric(key, float(value), step=step)


def _log_flat_params(data: dict[str, Any], prefix: str, depth: int = 0) -> None:
    if depth > 2:
        return
    mlflow = _import_mlflow()
    for key, value in data.items():
        param_key = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
        if isinstance(value, dict):
            _log_flat_params(value, param_key, depth + 1)
            continue
        if value is None or isinstance(value, (list, dict)):
            continue
        mlflow.log_param(param_key, str(value)[:500])
