"""Detection fusion with disagreement reporting."""

from __future__ import annotations

from smart_parking.config import FusionConfig
from smart_parking.detection.normalize import detections_from_batch
from smart_parking.pipeline.context import PipelineFrame
from smart_parking.types import Detection


def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter <= 0:
        return 0.0
    aa = (ax2 - ax1) * (ay2 - ay1)
    bb = (bx2 - bx1) * (by2 - by1)
    return inter / (aa + bb - inter + 1e-6)


def _nms(dets: list[Detection], iou_thr: float) -> list[Detection]:
    dets = sorted(dets, key=lambda d: d.confidence, reverse=True)
    kept: list[Detection] = []
    for d in dets:
        if all(_iou(d.bbox_xyxy, k.bbox_xyxy) < iou_thr for k in kept):
            kept.append(d)
    return kept


def count_disagreements(detr: list[Detection], yolo: list[Detection], iou_thr: float) -> int:
    """Pairs with no IoU match across models."""
    unmatched = 0
    for d in detr:
        if not any(_iou(d.bbox_xyxy, y.bbox_xyxy) >= iou_thr for y in yolo):
            unmatched += 1
    for y in yolo:
        if not any(_iou(y.bbox_xyxy, d.bbox_xyxy) >= iou_thr for d in detr):
            unmatched += 1
    return unmatched


def fuse_frame(frame: PipelineFrame, cfg: FusionConfig) -> list[Detection]:
    """Apply configured fusion strategy."""
    detr = (
        detections_from_batch(frame.detr_batch)
        if frame.detr_batch
        else []
    )
    yolo = (
        detections_from_batch(frame.yolo_batch)
        if frame.yolo_batch
        else []
    )
    frame.fusion_disagreements = count_disagreements(detr, yolo, cfg.iou_threshold)

    if cfg.strategy == "yolo_only":
        return yolo
    if cfg.strategy == "detr_only":
        return detr
    if cfg.strategy == "union":
        return _nms(detr + yolo, cfg.iou_threshold)
    # weighted_nms: scale confidences then NMS
    scaled: list[Detection] = []
    for d in detr:
        scaled.append(
            Detection(
                bbox_xyxy=d.bbox_xyxy,
                confidence=d.confidence * cfg.detr_weight,
                class_id=d.class_id,
                class_name=d.class_name,
            )
        )
    for y in yolo:
        scaled.append(
            Detection(
                bbox_xyxy=y.bbox_xyxy,
                confidence=y.confidence * cfg.yolo_weight,
                class_id=y.class_id,
                class_name=y.class_name,
            )
        )
    return _nms(scaled, cfg.iou_threshold)
