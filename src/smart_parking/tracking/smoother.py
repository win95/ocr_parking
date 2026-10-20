"""Per-slot temporal smoothing."""

from __future__ import annotations

from collections import defaultdict, deque

from smart_parking.config import SmoothingConfig
from smart_parking.types import SlotState


class SlotSmoother:
    """Majority vote with hysteresis per slot."""

    def __init__(self, slot_ids: list[str], cfg: SmoothingConfig) -> None:
        self._cfg = cfg
        self._history: dict[str, deque[bool]] = {
            sid: deque(maxlen=cfg.window) for sid in slot_ids
        }
        self._state: dict[str, bool] = {sid: False for sid in slot_ids}

    def update(self, raw: dict[str, bool]) -> dict[str, SlotState]:
        out: dict[str, SlotState] = {}
        for sid, hist in self._history.items():
            hist.append(raw.get(sid, False))
            votes = sum(1 for v in hist if v)
            prev = self._state[sid]
            if not prev and votes >= self._cfg.t_on:
                self._state[sid] = True
            elif prev and votes <= (self._cfg.window - self._cfg.t_off):
                self._state[sid] = False
            out[sid] = SlotState(slot_id=sid, occupied=self._state[sid])
        return out
