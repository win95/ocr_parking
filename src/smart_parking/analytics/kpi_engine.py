"""KPI computation and event logging."""

from __future__ import annotations

import json
import time
from pathlib import Path

from smart_parking.types import SlotState


class KPIEngine:
    """Track utilization and slot enter/exit events."""

    def __init__(self, total_slots: int, log_path: str) -> None:
        self._total = total_slots
        self._log_path = Path(log_path)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._prev: dict[str, bool] = {}
        self._enter_ts: dict[str, float] = {}

    def update(self, states: dict[str, SlotState]) -> dict:
        occupied = sum(1 for s in states.values() if s.occupied)
        free = self._total - occupied
        util = (occupied / self._total * 100.0) if self._total else 0.0
        self._emit_transitions(states)
        return {
            "occupied_count": occupied,
            "free_count": free,
            "total_slots": self._total,
            "utilization_pct": util,
        }

    def _emit_transitions(self, states: dict[str, SlotState]) -> None:
        now = time.time()
        for sid, st in states.items():
            was = self._prev.get(sid, False)
            if st.occupied and not was:
                self._enter_ts[sid] = now
                self._write_event({"type": "slot_enter", "slot_id": sid, "ts": now})
            if not st.occupied and was:
                start = self._enter_ts.pop(sid, now)
                dwell = now - start
                self._write_event(
                    {
                        "type": "slot_exit",
                        "slot_id": sid,
                        "ts": now,
                        "dwell_seconds": dwell,
                    }
                )
            self._prev[sid] = st.occupied

    def _write_event(self, payload: dict) -> None:
        with self._log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")
