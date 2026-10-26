"""DETR-R50-DC5 detector (optional transformers dependency)."""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from smart_parking.config import DetrConfig
from smart_parking.types import Detection

_COCO_VEHICLE = {3: "car", 4: "motorcycle", 6: "bus", 8: "truck"}

_LONG_EDGE_RATIO = 1.66


def torch_device(device: str) -> str:
    """Map an ultralytics-style device id ("0") to a torch device ("cuda:0")."""
    dev = (device or "cpu").strip()
    if dev.isdigit():
        return f"cuda:{dev}"
    return dev


def _resize_for_detr(image: np.ndarray, size: int) -> np.ndarray:
    """Resize to the processor's own geometry, but with a much faster resampler.

    PIL's resize inside DetrImageProcessor costs ~25 ms on a 720p frame; cv2
    does the same job in ~2 ms. The processor is then called with
    do_resize=False so the geometry is identical.
    """
    h, w = image.shape[:2]
    scale = size / float(min(h, w))
    long_edge = size * _LONG_EDGE_RATIO
    if max(h, w) * scale > long_edge:
        scale = long_edge / float(max(h, w))
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))
    if (nw, nh) == (w, h):
        return image
    return cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)


class DetrR50Detector:
    """facebook/detr-resnet-50-dc5 via Hugging Face transformers."""

    def __init__(self, cfg: DetrConfig) -> None:
        self._cfg = cfg
        self._device = torch_device(cfg.device)
        self._processor = None
        self._model = None
        self._load()

    def _load(self) -> None:
        try:
            from transformers import DetrForObjectDetection, DetrImageProcessor
        except ImportError as exc:
            raise RuntimeError("transformers required for DETR") from exc
        size = int(self._cfg.size)
        self._processor = DetrImageProcessor.from_pretrained(
            self._cfg.model_id,
            size={
                "shortest_edge": size,
                "longest_edge": int(size * _LONG_EDGE_RATIO),
            },
        )
        self._model = DetrForObjectDetection.from_pretrained(self._cfg.model_id)
        self._model.to(self._device)
        self._model.eval()

    def detect(self, image: np.ndarray) -> list[Detection]:
        if self._model is None or self._processor is None:
            return []
        rgb = Image.fromarray(_resize_for_detr(image, int(self._cfg.size))[:, :, ::-1])
        inputs = self._processor(images=rgb, return_tensors="pt", do_resize=False)
        inputs = {k: v.to(self._device) for k, v in inputs.items()}
        import torch

        with torch.inference_mode():
            outputs = self._model(**inputs)
        target = self._processor.post_process_object_detection(
            outputs,
            threshold=self._cfg.confidence,
            target_sizes=torch.tensor(
                [[image.shape[0], image.shape[1]]], device=self._device
            ),
        )[0]
        out: list[Detection] = []
        for score, label, box in zip(
            target["scores"], target["labels"], target["boxes"]
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
            import timm  # noqa: F401
            import transformers  # noqa: F401

            return True
        except ImportError:
            return False
