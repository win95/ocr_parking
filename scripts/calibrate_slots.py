#!/usr/bin/env python3
"""Interactive slot polygon calibration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    img = cv2.imread(args.image)
    if img is None:
        raise SystemExit(f"cannot read image: {args.image}")

    h, w = img.shape[:2]
    zones: list[dict] = []
    current: list[list[float]] = []
    zone_idx = 1

    def redraw() -> None:
        view = img.copy()
        for z in zones:
            pts = np.array(z["polygon"], dtype=np.int32)
            cv2.polylines(view, [pts], True, (0, 255, 0), 2)
        if len(current) >= 2:
            pts = np.array(current, dtype=np.int32)
            cv2.polylines(view, [pts], False, (0, 255, 255), 2)
        for p in current:
            cv2.circle(view, (int(p[0]), int(p[1])), 4, (255, 0, 0), -1)
        cv2.imshow("calibrate", view)

    def on_mouse(event: int, x: int, y: int, *_args: object) -> None:
        nonlocal current
        if event == cv2.EVENT_LBUTTONDOWN:
            current.append([float(x), float(y)])
            redraw()

    cv2.namedWindow("calibrate")
    cv2.setMouseCallback("calibrate", on_mouse)
    redraw()

    while True:
        key = cv2.waitKey(20) & 0xFF
        if key == ord("q"):
            break
        if key == ord("n") and len(current) >= 3:
            zones.append(
                {"id": f"S-{zone_idx:02d}", "zone": "A", "polygon": current}
            )
            zone_idx += 1
            current = []
            redraw()
        if key == ord("s"):
            out = {
                "zones": zones,
                "meta": {"width": w, "height": h, "source": Path(args.image).name},
            }
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
            print(f"saved {args.out}")

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
