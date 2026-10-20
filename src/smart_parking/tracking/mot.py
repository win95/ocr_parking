"""Lightweight IoU tracker with coasting."""

from __future__ import annotations

from smart_parking.config import TrackingConfig
from smart_parking.types import Detection, Track


def _iou(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / (area_a + area_b - inter + 1e-6)


class SimpleTracker:
    """Greedy IoU association with coasting."""

    def __init__(self, cfg: TrackingConfig) -> None:
        self._cfg = cfg
        self._tracks: dict[int, Track] = {}
        self._miss: dict[int, int] = {}
        self._next_id = 1

    def update(self, detections: list[Detection]) -> list[Track]:
        assigned: set[int] = set()
        for det in detections:
            best_id, best_iou = None, self._cfg.iou_threshold
            for tid, tr in self._tracks.items():
                if tid in assigned:
                    continue
                score = _iou(det.bbox_xyxy, tr.bbox_xyxy)
                if score >= best_iou:
                    best_iou, best_id = score, tid
            if best_id is None:
                tid = self._next_id
                self._next_id += 1
                self._tracks[tid] = Track(
                    track_id=tid,
                    bbox_xyxy=det.bbox_xyxy,
                    confidence=det.confidence,
                )
                self._miss[tid] = 0
                assigned.add(tid)
                continue
            self._tracks[best_id] = Track(
                track_id=best_id,
                bbox_xyxy=det.bbox_xyxy,
                confidence=det.confidence,
                coasting=False,
            )
            self._miss[best_id] = 0
            assigned.add(best_id)

        for tid in list(self._tracks.keys()):
            if tid in assigned:
                continue
            self._miss[tid] = self._miss.get(tid, 0) + 1
            if self._miss[tid] > self._cfg.coast_frames:
                del self._tracks[tid]
                del self._miss[tid]
            else:
                tr = self._tracks[tid]
                self._tracks[tid] = Track(
                    track_id=tr.track_id,
                    bbox_xyxy=tr.bbox_xyxy,
                    confidence=tr.confidence * 0.95,
                    coasting=True,
                )
        return list(self._tracks.values())
