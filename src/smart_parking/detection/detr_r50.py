"""DETR-R50-DC5 detector (optional transformers dependency)."""

from __future__ import annotations

import numpy as np
from PIL import Image

from smart_parking.config import DetrConfig
from smart_parking.types import Detection

_COCO_VEHICLE = {3: "car", 6: "bus", 8: "truck"}


class DetrR50Detector:
    """facebook/detr-resnet-50-dc5 via Hugging Face transformers."""

    def __init__(self, cfg: DetrConfig) -> None:
        self._cfg = cfg
        self._processor = None
        self._model = None
        self._load()

    def _load(self) -> None:
        try:
            from transformers import DetrForObjectDetection, DetrImageProcessor
        except ImportError as exc:
            raise RuntimeError("transformers required for DETR") from exc
        self._processor = DetrImageProcessor.from_pretrained(self._cfg.model_id)
        self._model = DetrForObjectDetection.from_pretrained(self._cfg.model_id)
        self._model.to(self._cfg.device)
        self._model.eval()

    def detect(self, image: np.ndarray) -> list[Detection]:
        if self._model is None or self._processor is None:
            return []
        rgb = Image.fromarray(image[:, :, ::-1])
        inputs = self._processor(images=rgb, return_tensors="pt")
        inputs = {k: v.to(self._cfg.device) for k, v in inputs.items()}
        import torch

        with torch.no_grad():
            outputs = self._model(**inputs)
        target = self._processor.post_process_object_detection(
            outputs,
            threshold=self._cfg.confidence,
            target_sizes=torch.tensor([[image.shape[0], image.shape[1]]]),
        )[0]
        out: list[Detection] = []
        for score, label, box in zip(
            target["scores"], target["labels"], target["boxes"], strict=False
        ):
            cid = int(label)
            name = _COCO_VEHICLE.get(cid, self._model.config.id2label.get(cid, str(cid)))
            if self._cfg.vehicle_only and cid not in _COCO_VEHICLE:
                continue
            xyxy = box.tolist()
            out.append(
                Detection(
                    bbox_xyxy=(xyxy[0], xyxy[1], xyxy[2], xyxy[3]),
                    confidence=float(score),
                    class_id=cid,
                    class_name=str(name),
                )
            )
        return out

    @staticmethod
    def is_available() -> bool:
        try:
            import transformers  # noqa: F401

            return True
        except ImportError:
            return False
