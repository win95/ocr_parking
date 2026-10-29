"""Parking slot polygon definitions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class SlotZone(BaseModel):
    id: str
    zone: str = "default"
    polygon: list[list[float]]

    @field_validator("polygon")
    @classmethod
    def min_points(cls, poly: list[list[float]]) -> list[list[float]]:
        if len(poly) < 3:
            raise ValueError("polygon needs at least 3 points")
        return poly


class SlotsFile(BaseModel):
    zones: list[SlotZone]
    meta: dict = Field(default_factory=dict)


@dataclass(frozen=True)
class Slot:
    """Runtime slot geometry."""

    id: str
    zone: str
    polygon: list[tuple[float, float]]
    meta_width: float | None = None
    meta_height: float | None = None


def load_slots(path: str | Path) -> list[Slot]:
    """Load and validate slots JSON."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    parsed = SlotsFile.model_validate(raw)
    width = parsed.meta.get("width")
    height = parsed.meta.get("height")
    slots: list[Slot] = []
    for z in parsed.zones:
        poly = [(float(p[0]), float(p[1])) for p in z.polygon]
        if width is not None and height is not None:
            _validate_bounds(poly, float(width), float(height))
        slots.append(
            Slot(
                id=z.id,
                zone=z.zone,
                polygon=poly,
                meta_width=float(width) if width is not None else None,
                meta_height=float(height) if height is not None else None,
            )
        )
    return slots


def _validate_bounds(poly: list[tuple[float, float]], w: float, h: float) -> None:
    for x, y in poly:
        if x < 0 or y < 0 or x > w or y > h:
            raise ValueError(f"polygon point ({x},{y}) outside {w}x{h}")


def point_in_polygon(x: float, y: float, polygon: list[tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon test."""
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if ((y1 > y) != (y2 > y)) and (
            x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1
        ):
            inside = not inside
    return inside
