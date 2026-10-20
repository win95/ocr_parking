"""Pluggable KPI widgets."""

from __future__ import annotations

from typing import Protocol


class KPIWidget(Protocol):
    """Render one KPI line from snapshot dict."""

    def name(self) -> str:
        ...

    def value(self, snapshot: dict) -> str:
        ...


class UtilizationWidget:
    """Shows utilization percentage."""

    def name(self) -> str:
        return "Utilization"

    def value(self, snapshot: dict) -> str:
        return f"{snapshot.get('utilization_pct', 0.0):.1f}%"


class OccupiedWidget:
    """Shows occupied / total."""

    def name(self) -> str:
        return "Occupied"

    def value(self, snapshot: dict) -> str:
        return f"{snapshot.get('occupied_count', 0)}/{snapshot.get('total_slots', 0)}"


DEFAULT_WIDGETS: list[KPIWidget] = [OccupiedWidget(), UtilizationWidget()]
